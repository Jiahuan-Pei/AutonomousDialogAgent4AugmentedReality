import torch
from peft import PeftConfig
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from tqdm import tqdm
from peft import LoraConfig
import numpy as np
import random
import torch.backends.cudnn as cudnn
from datasets import load_dataset, concatenate_datasets, DatasetDict
from datetime import datetime
from sklearn.model_selection import train_test_split


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


class Config():
    # Hyperparameters
    max_length = 512  # This was an appropriate max length for my dataset
    max_steps = 1000  # [500, 1000, 10000]

    # Data
    project = "vox-finetune"
    base_model_name = "llama-2-7b-chat"
    storage_dir = '/media/PampusData/jpei'
    dataset_names = [
        'teach',
        'gpt_teacher',
        'gpt4tools',
        'camel'
    ]
    data_name = '-'.join(dataset_names)
    teach_data_dir = "/media/PampusData/jpei/teach-dataset/edh_instances"

    # Model
    # base_model_id = "meta-llama/Llama-2-7b-hf"
    base_model_id = f'{storage_dir}/transformer_data/{base_model_name}'  # local model dir: /media/PampusData/jpei/transformer_data/llama-2-7b-chat
    run_name = f'{base_model_name}-{data_name}-{datetime.now().strftime("%Y-%m-%d-%H-%M")}'
    ft_model_id = f'{storage_dir}/{project}/{run_name}'  # /media/PampusData/vox-finetune/llama-2-7b-chat
    checkpoint_name = f'checkpoint-{max_steps}'
    ft_ckpt_id = f'{ft_model_id}/{checkpoint_name}'

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

    tokenizer = AutoTokenizer.from_pretrained(
        base_model_id,
        padding_side="left",
        add_eos_token=True,
        add_bos_token=True,
    )
    tokenizer.pad_token = tokenizer.eos_token

    set_random_seed() # fix randomness


def wandb():
    import wandb, os
    wandb.login()

    wandb_project = "vox-finetune"
    if len(wandb_project) > 0:
        os.environ["WANDB_PROJECT"] = wandb_project


def formatting_func(example):
    text = f"### Question: {example['input']}\n ### Answer: {example['output']}"
    return text


def generate_and_tokenize_prompt(prompt):
    return config.tokenizer(formatting_func(prompt))


def generate_and_tokenize_prompt2(prompt):
    result = config.tokenizer(
        formatting_func(prompt),
        truncation=True,
        max_length=config.max_length,
        padding="max_length",
    )
    result["labels"] = result["input_ids"].copy()
    return result


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


def load_local_dataset(name):
    if name == 'teach':
        # Preprocessed by teach_data_exploration.ipynb and save at teach_data_dir
        teach_data_dir = "/media/PampusData/jpei/teach-dataset/edh_instances"
        train_dataset = load_dataset('json', data_files=f'{teach_data_dir}/teach_edh_train.jsonl', split='train')
        eval_dataset = load_dataset('json', data_files=f'{teach_data_dir}/teach_edh_valid.jsonl', split='train')
        test_dataset = load_dataset('json', data_files=f'{teach_data_dir}/teach_edh_test.jsonl', split='train')
        local_dataset = DatasetDict({"train": train_dataset, "validation": eval_dataset, "test": test_dataset})
    return local_dataset


def load_train_valid_test_datasets(dataset_names, mode='train'):
    # Load a dataset and print the first example in the training set
    dataset_list = []

    if 'teach' in dataset_names:
        dataset_list.append(load_local_dataset('teach'))
    if 'gpt_teacher' in dataset_names:
        gpt_teacher_dataset = load_dataset("causal-lm/gpt_teacher", split=['train', 'validation[:50%]', 'validation[50%:]'])
        dataset_list.append(gpt_teacher_dataset)
    if 'gpt4tools' in dataset_names:
        gpt4tools_dataset = load_dataset("causal-lm/gpt4tools", split=['train', 'validation[:50%]', 'validation[50%:]'])
        dataset_list.append(gpt4tools_dataset)
    if 'camel' in dataset_names:
        camel_dataset = load_dataset("causal-lm/camel", split=['train', 'validation[:50%]', 'validation[50%:]'])
        dataset_list.append(camel_dataset)

    if mode == 'train':
        # Combine datasets
        combined_dataset_train = concatenate_datasets([d['train'] for d in dataset_list])
        validation_dataset_list = []
        for d in dataset_list:
            if 'test' not in d:
                validation_dataset_list.append(d[1])    # .remove_columns("instruction")
            else:
                validation_dataset_list.append(['validation'])

        combined_dataset_valid = concatenate_datasets(validation_dataset_list)

        # Tokenize dateaset
        tokenized_train_dataset = combined_dataset_train.map(generate_and_tokenize_prompt2)
        tokenized_val_dataset = combined_dataset_valid.map(generate_and_tokenize_prompt2)

        return tokenized_train_dataset, tokenized_val_dataset
    elif mode == 'test':
        test_dataset_list = []
        for d in dataset_list:
            if 'test' in d:
                test_dataset_list.append(d['test'])
            else:
                test_dataset_list.append(d[2])
        combined_dataset_test = concatenate_datasets(test_dataset_list)
        test_dataset_list.append(combined_dataset_test)
        return test_dataset_list


def load_base_model(config):
    base_model = AutoModelForCausalLM.from_pretrained(
        config.base_model_id,
        quantization_config=config.bnb_config
    )
    return base_model


def load_peft_model(config):
    peft_config = PeftConfig.from_pretrained(config.ft_model_id)
    peft_model = AutoModelForCausalLM.from_pretrained(
        peft_config.base_model_name_or_path,
        return_dict=True,
        quantization_config=config.bnb_config,
        device_map="auto",
        trust_remote_code=True
    )
    return peft_model


def load_models(config):
    print('Loading finetuned model:')
    peft_model = load_peft_model(config)
    print('Loading raw model:')
    base_model = load_base_model(config)
    return base_model, peft_model


def set_accelerator():
    from accelerate import FullyShardedDataParallelPlugin, Accelerator
    from torch.distributed.fsdp.fully_sharded_data_parallel import FullOptimStateDictConfig, FullStateDictConfig

    fsdp_plugin = FullyShardedDataParallelPlugin(
        state_dict_config=FullStateDictConfig(offload_to_cpu=True, rank0_only=False),
        optim_state_dict_config=FullOptimStateDictConfig(offload_to_cpu=True, rank0_only=False),
    )

    accelerator = Accelerator(fsdp_plugin=fsdp_plugin)
    return accelerator


# config = Config()