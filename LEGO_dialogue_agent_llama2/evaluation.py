"""
Submit:
    nohup python evaluation.py > output.log 2>&1 &
Check:
    ps aux | grep "evaluation.py"
GPU Usage:
    8912MiB / 24564MiB
"""
import torch
from peft import PeftConfig
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from tqdm import tqdm
import json

from utils import *

from transformers import pipeline
from datasets import load_metric
from rouge import Rouge
# from evaluate import load

# perplexity = load("perplexity", module_type="metric")


def compute_perplexity(model, tokenizer, text):
    input_ids = tokenizer.encode(text, return_tensors="pt")
    with torch.no_grad():
        logits = model(input_ids).logits
    perplexity = torch.exp(torch.nn.functional.cross_entropy(logits.view(-1, logits.shape[-1]), input_ids.view(-1)))
    return perplexity.item()


def compute_perplexity(model, tokenizer, text):
    input_ids = tokenizer.encode(text, return_tensors="pt")
    with torch.no_grad():
        logits = model(input_ids).logits
    perplexity = torch.exp(torch.nn.functional.cross_entropy(logits.view(-1, logits.shape[-1]), input_ids.view(-1)))
    return perplexity.item()


def compute_metrics(evaluation_results, tokenizer):
    """
    :param evaluation_result:
    # Example usage:
    evaluation_results = {
        'input': "Input prompt",
        'base_generated': "Generated response by base model",
        'check_generated': "Generated response by check model",
        'reference': "Reference response",
    }
    :param tokenizer:
    :return:
    """
    all_bleu_base = []
    all_bleu_check = []
    all_rouge_base = []
    all_rouge_check = []
    all_overlap_base = []
    all_overlap_check = []


    # Initialize BLEU metric
    bleu_metric = load_metric("bleu")
    # Initialize ROUGE metric
    rouge_metric = Rouge()

    for evaluation_result in evaluation_results:
        # Tokenize reference and generated responses
        references = [evaluation_result['reference']]
        base_generated = [evaluation_result['base_generated']]
        check_generated = [evaluation_result['check_generated']]

        # Compute BLEU scores
        bleu_scores_base = bleu_metric.compute(predictions=base_generated, references=references)
        bleu_scores_check = bleu_metric.compute(predictions=check_generated, references=references)

        # Compute ROUGE scores
        rouge_scores_base = rouge_metric.get_scores(base_generated[0], references[0])
        rouge_scores_check = rouge_metric.get_scores(check_generated[0], references[0])

        # Compute token overlap between generated and reference
        reference_tokens = set(tokenizer.tokenize(references[0]))
        base_generated_tokens = set(tokenizer.tokenize(base_generated[0]))
        check_generated_tokens = set(tokenizer.tokenize(check_generated[0]))
        overlap_base = len(reference_tokens.intersection(base_generated_tokens))
        overlap_check = len(reference_tokens.intersection(check_generated_tokens))

        # Aggregate metrics for each sample
        all_bleu_base.append(bleu_scores_base['score'])
        all_bleu_check.append(bleu_scores_check['score'])
        all_rouge_base.append(rouge_scores_base[0]['rouge-1']['f'])
        all_rouge_check.append(rouge_scores_check[0]['rouge-1']['f'])
        all_overlap_base.append(overlap_base)
        all_overlap_check.append(overlap_check)

    # Compute mean or other aggregation for corpus-level metrics
    corpus_metrics = {
        'Mean_BLEU_Base': np.mean(all_bleu_base),
        'Mean_BLEU_Check': np.mean(all_bleu_check),
        'Mean_ROUGE_Base': np.mean(all_rouge_base),
        'Mean_ROUGE_Check': np.mean(all_rouge_check),
        'Mean_Overlap_Base': np.mean(all_overlap_base),
        'Mean_Overlap_Check': np.mean(all_overlap_check),
    }

    return corpus_metrics


def main_evaluation(base_model=None, check_model=None, check_model_id=None):
    config = Config()
    tokenizer = config.tokenizer

    # Load test datasets
    test_dataset_list = load_train_valid_test_datasets(config.dataset_names, mode='test')

    # Load two models before and after fine-tuning
    if base_model and check_model:
        pass
    else:
        config.ft_model_id = check_model_id
        base_model, check_model = load_models(config)

    # Set the valuation mode of the models
    base_model.eval()
    check_model.eval()

    # Load test dataset

    # Initialize a list to store generated and reference response pairs
    base_perplexity_list = []
    check_perplexity_list = []

    dataset_names = config.dataset_names + ['combination']

    # Evaluate the model on the test dataset
    for i, test_dataset in enumerate(test_dataset_list):
        dataset_name = dataset_names[i]
        base_predictions = []
        check_predictions = []
        evaluation_results = []
        for example in tqdm(test_dataset):
            input_prompt = example['input']
            reference_response = example['output']

            # Tokenize the input prompt
            model_input = tokenizer(input_prompt, return_tensors="pt").to("cuda")

            # Generate a response from the model
            with torch.no_grad():
                # generated_ids = check_model.generate(input_ids, max_new_tokens=256, pad_token_id=2, padding_side='left')
                base_generated_ids = base_model.generate(**model_input, max_new_tokens=256, pad_token_id=2)
                check_generated_ids = check_model.generate(**model_input, max_new_tokens=256, pad_token_id=2)

            # Decode the generated response
            base_generated_response = tokenizer.decode(base_generated_ids[0], skip_special_tokens=True)
            check_generated_response = tokenizer.decode(check_generated_ids[0], skip_special_tokens=True)
            base_predictions.append(base_generated_response)
            check_predictions.append(check_generated_response)

            # Save the generated and reference responses
            evaluation_results.append({
                'input': input_prompt,
                'base_generated': base_generated_response,
                'check_generated': check_generated_response,
                'reference': reference_response
            })

        # print(evaluation_results)
        metrics = compute_metrics(evaluation_results, tokenizer)

        # metrics['Mean_Perplexity_Base'] = perplexity.compute(predictions=base_predictions, model_id='gpt2')
        # metrics['Mean_Perplexity_Check'] = perplexity.compute(predictions=check_predictions, model_id='gpt2')

        print(f'{i}\t{dataset_name}\n{metrics}\n'+'-'*10)

        # Save the generated and reference responses to a JSON file
        with open(f'{config}/{dataset_name}_evaluation_results.json', 'w') as json_file:
            json.dump(evaluation_results, json_file)  # indent=2


    return


if __name__ == '__main__':

    main_evaluation(check_model_id='/media/PampusData/jpei/vox-finetune/llama-2-7b-chat-teach-gpt_teacher-gpt4tools-camel-2023-11-28-14-12')
