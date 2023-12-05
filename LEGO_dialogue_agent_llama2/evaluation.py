"""
Submit:
    nohup python evaluation.py > evaluation.output.log 2>&1 &
Check:
    ps aux | grep "evaluation.py"
GPU Usage:
    8912MiB / 24564MiB
"""
import os.path

import torch
from peft import PeftConfig
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from tqdm import tqdm
import json

from utils import Config, load_train_valid_test_datasets, load_base_model

import transformers
from datasets import load_metric
from rouge import Rouge
import evaluate
import numpy as np
from langchain.llms import HuggingFacePipeline


def fast_compute_metrics(predictions, references, tokenizer):
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


def main_evaluation(config, eval_model=None, eval_dataset_list=None):
    # Load two models before and after fine-tuning
    if eval_model is None:
        model = load_base_model(config)
        print('Load base model.')
    else:
        model = eval_model
        print('Reuse loaded the model.')

    # Set the valuation mode of the models
    model.eval()

    # Load tokenizer
    tokenizer = config.tokenizer
    max_tokens = config.max_length
    batch_size = 8

    # Load test datasets
    if eval_dataset_list is None:
        test_dataset_list = load_train_valid_test_datasets(config.dataset_names, mode='test')
        dataset_names = config.dataset_names + ['combination']
    else:
        test_dataset_list = eval_dataset_list

    # Evaluate the model on the test dataset
    for i, test_dataset in enumerate(test_dataset_list):
        dataset_name = dataset_names[i] if eval_dataset_list is None else 'demo_dataset'
        print(dataset_name + '-'*10 + str(len(test_dataset)))
        # evaluation_results = []
        inputs = [example['input'] for example in test_dataset]
        references = [example['output'] for example in test_dataset]
        predictions = []
        perplexity_list = []

        # Tokenize the entire test dataset
        tokenized_inputs = tokenizer([f"### Question: {example['input']}\n ### Answer: " for example in test_dataset], return_tensors="pt", padding=True, truncation=True, max_length=max_tokens)

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
                batch_perplexity = torch.exp(cross_entropy_loss).item()
                perplexity_list.append(batch_perplexity)

            generate_text = transformers.pipeline(
                model=model,
                batch_size=batch_size,
                tokenizer=tokenizer,
                return_full_text=True,  # langchain expects the full text
                task='text-generation',
                # we pass model parameters here too
                temperature=0.0,  # 'randomness' of outputs, 0.0 is the min and 1.0 the max
                max_new_tokens=512,  # mex number of tokens to generate in the output
                repetition_penalty=1.1  # without this output begins repeating
            )
            # batch_generated_responses = tokenizer.batch_decode(batch_generated_ids[0], skip_special_tokens=True)
            from langchain.llms import HuggingFacePipeline
            llm = HuggingFacePipeline(pipeline=generate_text)
            batch_generated_responses = llm(batch_generated_ids[0])

            predictions.extend(batch_generated_responses)

            # # Iterate over each example in the batch
            # for example_idx, generated_id in enumerate(generated_ids):
            #     # Compute perplexity
            #     logits_flat = logits[example_idx].view(-1, logits.size(-1))
            #     references_flat = batch_model_inputs["input_ids"][example_idx].view(-1)
            #
            #     # Check for NaN in logits
            #     if torch.isnan(logits_flat).any():
            #         print("NaN found in logits. Skipping example.")
            #         continue
            #
            #     # Check for infinite logits
            #     if not torch.isfinite(logits_flat).all():
            #         print("Infinite logits found. Skipping example.")
            #         continue
            #
            #     cross_entropy_loss = torch.nn.functional.cross_entropy(logits_flat, references_flat)
            #
            #     # Check for NaN in loss
            #     if torch.isnan(cross_entropy_loss):
            #         print("NaN found in cross-entropy loss. Skipping example.")
            #         continue
            #
            #     perplexity = torch.exp(cross_entropy_loss).item()
            #
            #     # Check for NaN in perplexity
            #     if np.isnan(perplexity):
            #         print("NaN found in perplexity. Skipping example.")
            #         continue
            #
            #     # Decode the generated response
            #     generated_response = tokenizer.decode(generated_id[0], skip_special_tokens=True)
            #
            #     # Save the generated and reference responses
            #     evaluation_results.append({
            #         'input': test_dataset[batch_start + example_idx]['input'],
            #         'prediction': generated_response,
            #         'reference': test_dataset[batch_start + example_idx]['output'],
            #         'perplexity': perplexity
            #     })

            # Monitor GPU memory usage
            current_memory_allocated = torch.cuda.memory_allocated()
            max_memory_allocated = torch.cuda.max_memory_allocated()
            print(f"Current Memory Allocated: {current_memory_allocated / (1024 ** 3):.2f} GB")
            print(f"Max Memory Allocated: {max_memory_allocated / (1024 ** 3):.2f} GB")
            # Empty GPU cache to release memory
            torch.cuda.empty_cache()

        # references = [result['reference'] for result in evaluation_results]
        # predictions = [result['prediction'] for result in evaluation_results]

        # Compute evaluation metrics
        metrics = fast_compute_metrics(references, predictions, tokenizer)

        # metrics['corpus_perplexity'] = np.nanmean([result['perplexity'] for result in evaluation_results])  # ignore nan
        metrics['corpus_perplexity'] = np.nanmean(perplexity_list)  # ignore nan

        print(json.dumps(metrics, indent=4))

        if not os.path.exists(config.output_dir):
            os.mkdir(config.output_dir)

        evaluation_results = [{"input": i, "reference": r, "prediction": p} for (i, r, p) in zip(*[inputs, references, predictions])]

        with open(f'{config.output_dir}/{dataset_name}_evaluation_results.json', 'w') as json_file:
            json.dump(evaluation_results, json_file, indent=2)

    return


def test_main_evaluation():
    config = Config()
    demo_dataset = load_dataset("Jiahuan/teach_edh", split='test[:1%]', use_auth_token=True)
    main_evaluation(config, eval_dataset_list=[demo_dataset])


if __name__ == '__main__':
    test_main_evaluation()
