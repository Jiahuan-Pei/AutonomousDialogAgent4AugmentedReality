"""
Submit:
    nohup python evaluation.py > evaluation.output.log 2>&1 &
    nohup python evaluation.py --dataset_id Jiahuan/vox_arta_lego --model_id meta-llama/Llama-2-7b-chat-hf > evaluation_llama2_arta_lego.log 2>&1 &
    nohup python evaluation.py --dataset_id Jiahuan/vox_arta_lego --model_id Jiahuan/voxreality-arta-lego-llama2-7b-chat > vox_arta_lego_evaluation.output.log 2>&1 &
    nohup python evaluation.py --model_id Jiahuan/voxreality-arta-llama2-7b-chat-v3 > finetune_teach_edh_evaluation.output.log 2>&1 &
    nohup python evaluation.py --model_id Jiahuan/gpt_teacher-llama2-7b-chat --dataset_id causal-lm/gpt_teacher > finetune_gpt_teacher_evaluation.output.log 2>&1 &
Check:
    ps aux | grep "evaluation.py"
    watch -n 1 nvidia-smi
GPU Usage:
    17GiB / 24GiB
"""
import os.path
import json
from tqdm import tqdm
import numpy as np
import torch
import transformers
from datasets import load_dataset
import evaluate
import argparse
from transformers import AutoTokenizer
from utils import load_model_singleGPU, formatting_func_inference


def fast_compute_metrics(predictions, references):
    """
    :param evaluation_result:
    # Example usage:
    evaluation_results = {
        'input': "Input prompt",
        'prediction': "Generated response",
        'reference': "Reference response",
    }
    :param tokenizer:
    :return:
    """
    bleu = evaluate.load("bleu")  # Measures the similarity between the generated text and reference text based on n-grams.
    rouge = evaluate.load('rouge')  # Evaluates the overlap between the generated text and reference text in terms of n-grams and word sequences.
    meteor = evaluate.load('meteor')  # Considers precision, recall, and harmonized mean of precision and recall with stemming and synonymy matching.

    corpus_metrics = {
        'BLEU': bleu.compute(predictions=predictions, references=[[result] for result in references]),
        'ROUGE': rouge.compute(predictions=predictions, references=references),
        'METOR': meteor.compute(predictions=predictions, references=references),
    }


    return corpus_metrics


def evaluate_main(model_id, dataset_id, output_dir, max_tokens, batch_size, split='test'):

    test_dataset = load_dataset(dataset_id, split=split, use_auth_token=True)

    model = load_model_singleGPU(model_id)
    # Set the valuation mode of the models
    model.eval()

    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        padding_side="left",
        add_eos_token=True,
        add_bos_token=True,
    )
    tokenizer.pad_token = tokenizer.eos_token

    inputs = [example['input'] for example in test_dataset]
    references = [example['output'] for example in test_dataset]
    predictions = []
    perplexity_list = []

    # Tokenize the entire test dataset
    tokenized_inputs = tokenizer([formatting_func_inference(example) for example in test_dataset], return_tensors="pt",
                                 padding=True, truncation=True, max_length=max_tokens)

    for batch_start in tqdm(range(0, len(tokenized_inputs['input_ids']), batch_size)):
        batch_model_inputs = {
            'input_ids': tokenized_inputs['input_ids'][batch_start:batch_start + batch_size],
            'attention_mask': tokenized_inputs['attention_mask'][batch_start:batch_start + batch_size]
        }
        batch_model_inputs = {k: v.to("cuda") for k, v in batch_model_inputs.items()}

        # Generate responses from the model
        with torch.no_grad():
            batch_generated_ids = model.generate(**batch_model_inputs, max_new_tokens=max_tokens, pad_token_id=2)
            batch_logits = model(**batch_model_inputs).logits
            batch_logits_flat = batch_logits.view(-1, batch_logits.size(-1))
            batch_references_flat = batch_model_inputs["input_ids"].view(-1)
            cross_entropy_loss = torch.nn.functional.cross_entropy(batch_logits_flat, batch_references_flat)
            batch_perplexity = torch.exp(cross_entropy_loss / len(batch_references_flat)).item()
            perplexity_list.append(batch_perplexity)

        batch_generated_responses = [t.split('### Response: ')[-1].strip() for t in tokenizer.batch_decode(batch_generated_ids, skip_special_tokens=True)]

        predictions.extend(batch_generated_responses)

        # Monitor GPU memory usage
        current_memory_allocated = torch.cuda.memory_allocated()
        max_memory_allocated = torch.cuda.max_memory_allocated()
        print(f"Current Memory Allocated: {current_memory_allocated / (1024 ** 3):.2f} GB")
        print(f"Max Memory Allocated: {max_memory_allocated / (1024 ** 3):.2f} GB")
        # Empty GPU cache to release memory
        torch.cuda.empty_cache()


    # Compute evaluation metrics
    metrics = fast_compute_metrics(references, predictions)

    # metrics['corpus_perplexity'] = np.nanmean([result['perplexity'] for result in evaluation_results])  # ignore nan
    metrics['corpus_perplexity'] = np.nanmean(perplexity_list)  # ignore nan

    evaluation_results = json.dumps(metrics, indent=4)

    print(evaluation_results)

    with open(f'{output_dir}/{model_id.split("/")[-1]}_{dataset_id.split("/")[-1]}_llm_evaluation_results.json', 'w') as json_file:
        json.dump(evaluation_results, json_file, indent=2)

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    evaluation_output = [{"input": i, "reference": r, "prediction": p} for (i, r, p) in
                          zip(*[inputs, references, predictions])]

    with open(f'{output_dir}/{model_id.split("/")[-1]}_{dataset_id.split("/")[-1]}_llm_evaluation_output.json', 'w') as json_file:
        json.dump(evaluation_output, json_file, indent=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_id', default='meta-llama/Llama-2-7b-chat-hf', type=str, help='the name or the abstract path of the model')
    parser.add_argument('--dataset_id', default='Jiahuan/teach_edh', type=str, help='the name or the abstract path of the dataset')
    parser.add_argument('--project_name', default='vox-finetune', type=str, help='the name or the abstract path of the dataset')
    parser.add_argument('--output_dir', default='/media/Blue2TB3/jpei/evaluation_results', type=str, help='the name or the abstract path of the dataset')
    parser.add_argument('--cache_dir', default='/media/Blue2TB3/jpei/cache-huggingface-2/datasets', type=str, help='the name or the abstract path of the dataset')
    parser.add_argument('--max_tokens', default=512, type=int, help='max number of tokens')
    parser.add_argument('--batch_size', default=8, type=int, help='batch size')
    parser.add_argument('--split', default='test', type=str, help='the split of the dataset to be evaluated.')
    args = parser.parse_args()
    evaluate_main(args.model_id, args.dataset_id, args.output_dir, args.max_tokens, args.batch_size)
