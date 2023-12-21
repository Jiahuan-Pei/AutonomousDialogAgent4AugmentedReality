"""
Submit:
    nohup python evaluation_pipeline.py --dataset_id Jiahuan/vox_arta_lego --model_id meta-llama/Llama-2-7b-chat-hf > llama2_arta_lego_evaluation_pipeline.output.log 2>&1 &
    nohup python evaluation_pipeline.py --dataset_id Jiahuan/vox_arta_lego --model_id Jiahuan/voxreality-arta-lego-llama2-7b-chat > vox_arta_lego_evaluation.output.log 2>&1 &
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
from langchain.llms import HuggingFacePipeline
from transformers import GenerationConfig, pipeline

from utils import Config, load_train_valid_test_datasets, load_model_singleGPU, load_peft_model_singleGPU, formatting_func_inference, load_peft_model, load_base_model


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


def evaluate_main(model_id, dataset_id, output_dir, max_tokens, batch_size):

    test_dataset = load_dataset(dataset_id, split='test', use_auth_token=True)

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

    generation_config = GenerationConfig.from_pretrained(model_id)
    generation_config.max_new_tokens = 512
    generation_config.temperature = 0.0001
    # generation_config.top_p = 0.95
    # generation_config.do_sample = True
    generation_config.repetition_penalty = 1.15

    generate_text = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        generation_config=generation_config,
        batch_size=batch_size,
        # temperature=0.0001
    )

    for batch_start in tqdm(range(0, len(inputs), batch_size)):
        # batch_generated_responses = llm(inputs[batch_start:batch_start + batch_size])
        batch_generated_responses = generate_text(inputs[batch_start:batch_start + batch_size], num_return_sequences=1)

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
    args = parser.parse_args()
    evaluate_main(args.model_id, args.dataset_id, args.output_dir, args.max_tokens, args.batch_size)
