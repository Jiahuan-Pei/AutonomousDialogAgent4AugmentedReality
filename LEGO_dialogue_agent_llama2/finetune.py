"""
Submit:
    nohup python finetune.py > finetune.output.log 2>&1 &
Check:
    ps aux | grep "finetune.py"
GPU Usage:
    8912MiB / 24564MiB
"""

from utils import *
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


def main_finetune():
    config = Config()
    tokenizer = config.tokenizer

    tokenized_train_dataset, tokenized_val_dataset, test_dataset_list = load_train_valid_test_datasets(config.dataset_names)

    model = load_base_model(config)

    accelerator = set_accelerator()

    model.gradient_checkpointing_enable()
    model = prepare_model_for_kbit_training(model)

    print(f'Base model:\n{model}')

    # model = get_peft_model(model, config.lora_config)
    print_trainable_parameters(model)

    # Apply the accelerator. You can comment this out to remove the accelerator.
    model = accelerator.prepare_model(model)

    print(f'Model with the LoRA adapters added:\n{model}')

    wandb()

    if torch.cuda.device_count() > 1:  # If more than 1 GPU
        model.is_parallelizable = True
        model.model_parallel = True

    # config.tokenizer.pad_token = config.tokenizer.eos_token

    trainer = transformers.Trainer(
        model=model,
        train_dataset=tokenized_train_dataset,
        eval_dataset=tokenized_val_dataset,
        # compute_metrics=compute_metrics,
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
        data_collator=transformers.DataCollatorForLanguageModeling(config.tokenizer, mlm=False),
        callbacks=[EarlyStoppingCallback(early_stopping_patience=10, early_stopping_threshold=0.01)]
    )

    model.config.use_cache = False  # silence the warnings. Please re-enable for inference!
    trainer.train()

    model.save_pretrained(config.ft_model_id)
    print('Saving fine-tuned model....')

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


if __name__ == '__main__':
    main_finetune()