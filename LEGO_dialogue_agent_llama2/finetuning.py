"""
Submit:
    nohup python finetuning.py > finetune.output.log 2>&1 &
Check:
    ps aux | grep "finetuning.py"
GPU Usage:
    8912MiB / 24564MiB
"""

from utils import *
from evaluation import main_evaluation
from peft import prepare_model_for_kbit_training, get_peft_model, PeftModel
import transformers
from datetime import datetime
from transformers import EarlyStoppingCallback, IntervalStrategy
from datasets import load_metric


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


def main_finetune():
    config = Config()
    tokenizer = config.tokenizer

    tokenized_train_dataset, tokenized_valid_dataset = load_train_valid_test_datasets(config.dataset_names)

    # Load base model
    model = load_base_model(config)
    print_trainable_parameters(model)
    print(f'Base model:\n{model}')

    # Prepare to train peft model
    model.gradient_checkpointing_enable()
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, config.lora_config)
    print_trainable_parameters(model)
    print(f'Model with the LoRA adapters added:\n{model}')

    # Apply the accelerator. You can comment this out to remove the accelerator.
    accelerator = set_accelerator()
    model = accelerator.prepare_model(model)

    wandb()

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
            output_dir=config.ft_model_id,
            warmup_steps=1,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=1,
            gradient_checkpointing=True,
            max_steps=config.max_steps,
            learning_rate=2.5e-5,  # Want a small lr for finetuning
            bf16=True,
            optim="paged_adamw_8bit",
            logging_dir="./logs",  # Directory for storing logs
            save_strategy="steps",  # Save the model checkpoint every logging step
            save_steps=50,  # Save checkpoints every 50 steps
            evaluation_strategy="steps",  # Evaluate the model every logging step
            eval_steps=50,  # Evaluate and save checkpoints every 50 steps
            do_eval=True,  # Perform evaluation at the end of training
            report_to="wandb",  # Comment this out if you don't want to use weights & baises
            run_name=f"{config.run_name}",  # Name of the W&B run (optional)，
            load_best_model_at_end=True
        ),
        data_collator=transformers.DataCollatorForLanguageModeling(tokenizer, mlm=False),
        callbacks=[EarlyStoppingCallback(early_stopping_patience=10, early_stopping_threshold=0.01)]
    )

    model.config.use_cache = False  # silence the warnings. Please re-enable for inference!

    # Train the model
    trainer.train()
    print('Saving fine-tuned model....')
    # Save the model
    try:
        model.save_pretrained(config.ft_model_id)  # it saves both the model weights and the associated tokenizer, so you can load the entire fine-tuned model later (config.json)
        tokenizer.save_pretrained(config.ft_model_id)
    except:
        print('Err: model saving does not work')
        try:
            trainer.save_model(config.ft_model_id)
            trainer.model.save_config(f"{config.ft_model_id}/config.json")
        except:
            print('Err: trainer saving does not work.')


if __name__ == '__main__':
    main_finetune()