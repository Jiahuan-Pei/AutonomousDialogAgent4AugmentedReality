"""
Submit:
    nohup python finetuning.py > finetune.output.log 2>&1 &
    nohup python finetuning.py --dataset=Jiahuan/vox_arta_lego --model_id_upload Jiahuan/voxreality-arta-lego-llama2-7b-chat > finetune_arta_lego_output.log 2>&1 &
    nohup python finetuning.py --dataset=Jiahuan/teach_action --model_id_upload Jiahuan/voxreality-arta-llama2-7b-chat-action > finetune_output_teach_action.log 2>&1 &
Check:
    ps aux | grep "finetuning.py"
GPU Usage:
    8912MiB / 24564MiB
"""

# from utils import *
import torch
from transformers import EarlyStoppingCallback, AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import prepare_model_for_kbit_training, get_peft_model, PeftModel, LoraConfig, AutoPeftModelForCausalLM
import transformers
from datetime import datetime
import math
import argparse
import random
import numpy as np
import torch.backends.cudnn as cudnn
from datasets import load_dataset, concatenate_datasets, DatasetDict


DEFAULT_SYSTEM_PROMPT = """
Below is a conversation between a human and an AI agent. Reply a response given the context.
""".strip()


def formatting_func_training(example):
    text = f"""### Instruction: {DEFAULT_SYSTEM_PROMPT}
    ### Context: {example['input']}
    ### Response: {example['output']}
    """.strip()
    return text

def generate_and_tokenize_prompt2(prompt):
    # set tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_id,
        padding_side="left",
        add_eos_token=True,
        add_bos_token=True,
    )
    tokenizer.pad_token = tokenizer.eos_token

    result = tokenizer(
        formatting_func_training(prompt),
        truncation=True,
        max_length=args.max_tokens,
        padding="max_length",
    )
    # result["labels"] = result["input_ids"].copy()
    result["labels"] = result["input_ids"].copy()
    return result


def load_train_valid_test_datasets(dataset_ids, mode='train'):
    # Load a dataset and print the first example in the training set
    dataset_list = []

    dataset_id_list = dataset_ids.split(',')

    for dataset_id in dataset_id_list:
        try:
            dataset = load_dataset(dataset_id, split=['train', 'validation', 'test'], cache_dir=args.cache_dir)
        except:
            dataset = load_dataset(dataset_id, split=['train', 'validation[:50%]', 'validation[50%:]'], cache_dir=args.cache_dir)

        dataset = DatasetDict({"train": dataset[0], "validation": dataset[1], "test": dataset[2]})
        dataset_list.append(dataset)

    if mode == 'train':
        # Combine datasets
        combined_dataset_train = concatenate_datasets([d['train'] for d in dataset_list])
        combined_dataset_valid = concatenate_datasets([d['validation'] for d in dataset_list])

        # Tokenize dateaset
        tokenized_train_dataset = combined_dataset_train.map(generate_and_tokenize_prompt2)
        tokenized_val_dataset = combined_dataset_valid.map(generate_and_tokenize_prompt2)

        return tokenized_train_dataset, tokenized_val_dataset
    elif mode == 'test':
        test_dataset_list = [d['test'] for d in dataset_list]
        return test_dataset_list


def set_random_seed(seed=None):
    if seed is None:
        seed = random.randrange(2 ** 32 - 1)

    np.random.seed(seed)
    torch.manual_seed(seed)
    random.seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        cudnn.enabled = True
        cudnn.benchmark = False
        cudnn.deterministic = True

    print('seed=%s' % seed)


def print_trainable_parameters(model):
    """
    Prints the number of trainable parameters in the model.
    """
    trainable_params = 0
    all_param = 0
    for _, param in model.named_parameters():
        all_param += param.numel()
        if param.requires_grad:
            trainable_params += param.numel()
    print(
        f"trainable params: {trainable_params} || all params: {all_param} || trainable%: {100 * trainable_params / all_param}"
    )


def eval_example(model, tokenizer, eval_prompt="Can you teach me how to cook?"):
    print(f"Evaluating prompt: {eval_prompt}")
    model_input = tokenizer(eval_prompt, return_tensors="pt").to("cuda")

    model.eval()
    with torch.no_grad():
        print(f"Model output: {tokenizer.decode(model.generate(**model_input, max_new_tokens=256, pad_token_id=2)[0], skip_special_tokens=True)}")


def set_accelerator():
    from accelerate import FullyShardedDataParallelPlugin, Accelerator
    from torch.distributed.fsdp.fully_sharded_data_parallel import FullOptimStateDictConfig, FullStateDictConfig

    fsdp_plugin = FullyShardedDataParallelPlugin(
        state_dict_config=FullStateDictConfig(offload_to_cpu=True, rank0_only=False),
        optim_state_dict_config=FullOptimStateDictConfig(offload_to_cpu=True, rank0_only=False),
    )

    accelerator = Accelerator(fsdp_plugin=fsdp_plugin)
    return accelerator


def set_config():
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    lora_config = LoraConfig(
        r=32,
        lora_alpha=64,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
            "lm_head",
        ],
        bias="none",
        lora_dropout=0.05,  # Conventional
        task_type="CAUSAL_LM",
    )
    return bnb_config, lora_config


def wandb(wandb_project):
    import wandb, os
    wandb.login()
    if len(wandb_project) > 0:
        os.environ["WANDB_PROJECT"] = wandb_project


def main_finetune(config):
    # fix randomness
    set_random_seed()

    # get config
    bnb_config, lora_config = set_config()

    # set tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        config.model_id,
        padding_side="left",
        add_eos_token=True,
        add_bos_token=True,
    )
    tokenizer.pad_token = tokenizer.eos_token

    tokenized_train_dataset, tokenized_valid_dataset = load_train_valid_test_datasets(config.dataset_id)

    run_name = f'{config.model_id}-{config.dataset_id.split("/")[-1]}-{datetime.now().strftime("%Y-%m-%d-%H-%M")}'
    ft_model_id = f'{config.root_dir}/{config.project_name}/{run_name}'  # /media/PampusData/vox-finetune/[run_name]

    # Load base model
    model = AutoModelForCausalLM.from_pretrained(
        config.model_id,
        return_dict=True,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )
    print_trainable_parameters(model)
    print(f'Base model:\n{model}')

    # Prepare to train peft model
    model.gradient_checkpointing_enable()
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, lora_config)
    print_trainable_parameters(model)
    print(f'Model with the LoRA adapters added:\n{model}')

    # Apply the accelerator. You can comment this out to remove the accelerator.
    accelerator = set_accelerator()
    model = accelerator.prepare_model(model)

    # Track at wandb
    wandb(wandb_project=config.project_name)

    if torch.cuda.device_count() > 1:  # If more than 1 GPU
        model.is_parallelizable = True
        model.model_parallel = True

    # config.tokenizer.pad_token = config.tokenizer.eos_token

    if torch.cuda.device_count() > 1:  # If more than 1 GPU
        model.is_parallelizable = True
        model.model_parallel = True

    trainer = transformers.Trainer(
        model=model,
        train_dataset=tokenized_train_dataset,
        eval_dataset=tokenized_valid_dataset,
        # compute_metrics=compute_metrics, # OOM
        args=transformers.TrainingArguments(
            output_dir=ft_model_id,
            warmup_steps=1,
            per_device_train_batch_size=16, # [2, 4]
            gradient_accumulation_steps=16, # 1
            gradient_checkpointing=True,
            num_train_epochs=5,
            max_steps=config.max_steps,
            # learning_rate=2.5e-5,  # Want a small lr for finetuning
            learning_rate=2e-4,  # Want a small lr for finetuning
            lr_scheduler_type="linear",
            bf16=True,
            optim="paged_adamw_8bit",
            logging_dir="./logs",  # Directory for storing logs
            save_strategy="steps",  # Save the model checkpoint every logging step
            # save_strategy="epoch",
            save_steps=50,  # Save checkpoints every 50 steps
            evaluation_strategy="steps",  # Evaluate the model every logging step
            # evaluation_strategy="epoch",  # Evaluate the model every logging step
            eval_steps=1,  # Evaluate and save checkpoints every 50 steps
            do_train=True,
            do_eval=True,  # Perform evaluation at the end of training
            logging_steps=1,
            report_to="wandb",  # Comment this out if you don't want to use weights & baises
            run_name=run_name,  # Name of the W&B run (optional)，
            load_best_model_at_end=True
        ),
        data_collator=transformers.DataCollatorForLanguageModeling(tokenizer, mlm=False),
        callbacks=[EarlyStoppingCallback(early_stopping_patience=10, early_stopping_threshold=0.01)]
    )

    model.config.use_cache = False  # silence the warnings. Please re-enable for inference!

    eval_results = trainer.evaluate()
    print(f"Base Perplexity: {math.exp(eval_results['eval_loss']):.2f}")

    # Train the model
    trainer.train()
    print('Saving fine-tuned model....')
    # Save only the adapter weights of the trained model
    try:
        model.save_pretrained(ft_model_id)  # it saves both the model weights and the associated tokenizer, so you can load the entire fine-tuned model later (config.json)
        tokenizer.save_pretrained(ft_model_id)
    except:
        print('Err: model saving does not work')
        try:
            trainer.save_model(ft_model_id)
            trainer.model.save_config(f"{ft_model_id}/config.json")
        except:
            print('Err: trainer saving does not work.')

    eval_results = trainer.evaluate()
    print(f"Perplexity: {math.exp(eval_results['eval_loss']):.2f}")

    ## Upload to Huggingface Hub
    tokenizer.push_to_hub(config.model_id_upload, use_auth_token=True)
    merge_and_upload(ft_model_id, args)


def merge_and_upload(ft_model_id, args):
    # Empty GPU cache to release memory
    torch.cuda.empty_cache()
    # ft_model_id = f'{args.output_dir}/llama-2-7b-chat-teach-2023-12-15-16-38'
    model = AutoPeftModelForCausalLM.from_pretrained(
        ft_model_id,
        low_cpu_mem_usage=True,
        device_map='auto',
        torch_dtype=torch.bfloat16
    )
    # Merge the base model and the adapter
    model = model.merge_and_unload(progressbar=True)
    model.save_pretrained(ft_model_id)
    # safetensors
    model.push_to_hub(args.model_id_upload, use_auth_token=True, safe_serialization=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_id', default='meta-llama/Llama-2-7b-chat-hf', type=str, help='the name or the abstract path of the base model')
    parser.add_argument('--model_id_upload', default='Jiahuan/voxreality-arta-llama2-7b-chat-v3', type=str, help='the name or the abstract path of the model to be uploaded to hub')
    parser.add_argument('--dataset_id', default='Jiahuan/teach_edh', type=str, help='the name or the abstract path of the dataset, or a concaticated list')
    parser.add_argument('--root_dir', default='/media/Blue2TB3/jpei/', type=str, help='the name of the root dir for storage')
    parser.add_argument('--project_name', default='vox-finetune', type=str, help='the name or the project')
    parser.add_argument('--output_dir', default='/media/Blue2TB3/jpei/vox-finetune/', type=str, help='the name or the abstract path of the dataset')
    parser.add_argument('--cache_dir', default='/media/Blue2TB3/jpei/cache-huggingface-2/datasets', type=str, help='the name or the abstract path of the dataset')
    parser.add_argument('--max_tokens', default=512, type=int, help='max number of tokens')
    parser.add_argument('--batch_size', default=8, type=int, help='batch size')
    parser.add_argument('--max_steps', default=2000, type=int, help='the name or the abstract path of the dataset')
    args = parser.parse_args()
    main_finetune(args)