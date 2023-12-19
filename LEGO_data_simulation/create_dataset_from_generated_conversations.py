import os
import json
import re
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm


def preprocess_conversations(input_folder, output_path):
    data = []

    total_txt_files = 0  # Variable to store the total number of .txt files

    # Additional variables for computing average number of utterances and utterance length
    total_utterances = 0
    total_characters = 0

    # Recursively traverse the directory
    for root, _, files in os.walk(input_folder):
        for filename in files:
            if filename.endswith(".txt"):
                total_txt_files += 1  # Increment the total count
                input_path = os.path.join(root, filename)

                # Read the content from the file
                with open(input_path, 'r', encoding='utf-8') as file:
                    content = file.read()

                # Perform preprocessing (customize as needed)
                preprocessed_content = preprocess_text(content)

                # Extract trainee-trainer conversation pairs
                conversation_pairs, utterance_count, character_count = extract_conversation_pairs(preprocessed_content)

                # Increment total utterance and character counts
                total_utterances += utterance_count
                total_characters += character_count

                # Append to the dataset
                data.extend(conversation_pairs)

    print(f"Total number of .txt files: {total_txt_files}")

    # Save the dataset to a JSONL file
    with open(output_path, 'w', encoding='utf-8') as jsonl_file:
        for example in data:
            jsonl_file.write(json.dumps(example, ensure_ascii=False) + '\n')

    # Compute dataset statistics
    statistics = compute_dataset_statistics(data, total_utterances, total_txt_files, total_characters)
    print(json.dumps(statistics, indent=4))

    # Visualize dataset statistics
    # visualize_statistics(statistics)
    return data


def preprocess_text(text):
    # Add your specific text preprocessing steps here
    # For example, removing special characters, extracting conversations, etc.
    # Modify this function based on the structure of your dataset

    # Example: Remove non-alphanumeric characters
    # cleaned_text = re.sub(r'[^a-zA-Z0-9\n\s]', '', text)
    cleaned_text = text
    return cleaned_text


def extract_conversation_pairs(content):
    # Assuming conversations are separated by newline characters
    utterances = content.split('\n\n')

    pairs = []
    current_role = None
    historical_utterances = []

    utterance_count = 0
    character_count = 0

    for utterance in utterances:
        # Identify the role based on ':'
        match = re.match(r'^(.*?): (.*)$', utterance)
        if match:
            role, message = match.groups()
            if role.lower() in ['trainer', 'trainee']:
                current_role = role
                historical_utterances.append(utterance)

                # Increment utterance and character counts
                utterance_count += 1
                character_count += len(message)

            if current_role.lower() == 'trainer':
                pairs.append({"input": "\n".join(historical_utterances), "output": message})

    return pairs, utterance_count, character_count


def compute_dataset_statistics(data, total_utterances, total_dialogues, total_characters):
    num_examples = len(data)
    avg_input_length = sum(len(example["input"]) for example in data) / num_examples
    avg_output_length = sum(len(example["output"]) for example in data) / num_examples

    # Compute average number of utterances per dialogue
    average_utterances_per_dialogue = total_utterances / total_dialogues if total_dialogues > 0 else 0

    # Compute average utterance length
    average_utterance_length = total_characters / total_utterances if total_utterances > 0 else 0

    statistics = {
        "#Dialogue": total_dialogues,
        "#Utterance": total_utterances,
        "#Examples": num_examples,
        "#AvgUttPerDial": average_utterances_per_dialogue,
        "average_utterance_length": average_utterance_length,
        "#AvgInputLength": avg_input_length,
        "#AvgOutputLength": avg_output_length,
    }

    return statistics


def visualize_statistics(statistics):
    # Create a bar plot for the dataset statistics
    sns.set(style="whitegrid")
    plt.figure(figsize=(8, 6))
    plt.bar(statistics.keys(), statistics.values(), color='skyblue')
    plt.title("Dataset Statistics")
    plt.ylabel("Value")
    plt.show()


def upload_to_hub(data):
    from datasets import load_dataset, DatasetDict, Dataset
    from huggingface_hub import login
    from sklearn.model_selection import train_test_split

    os.environ['HF_TOKEN'] = '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'
    # Replace 'your_token' with your actual Hugging Face API token
    api_token = os.environ['HF_TOKEN']

    # Log in to the Hugging Face Hub
    login(token=api_token)

    # Replace 'username/dataset-name' with your actual username and dataset name
    dataset_identifier = 'Jiahuan/vox_arta_lego'

    # Split the dataset into train, validation, and test sets
    train_data, test_data = train_test_split(data, test_size=0.2, random_state=42)
    train_data, val_data = train_test_split(train_data, test_size=0.1, random_state=42)
    train_dataset, val_dataset, test_dataset = Dataset.from_list(train_data), Dataset.from_list(val_data), Dataset.from_list(test_data)
    dataset = teach_object_dataset = DatasetDict({"train":train_dataset, "validation": val_dataset,"test":test_dataset})
    dataset.push_to_hub(dataset_identifier)

    # Print some information about the dataset
    print(dataset)


if __name__ == "__main__":
    input_folder_path = '/media/Blue2TB3/jpei/vox_arta_dataset/manuals/lego'  # Replace with the actual path to your input folder
    output_jsonl_path = '/media/Blue2TB3/jpei/vox_arta_dataset/manuals/lego/vox_arta_lego_dataset.jsonl'  # Replace with the desired path for the output JSONL file

    data = preprocess_conversations(input_folder_path, output_jsonl_path)

    upload_to_hub(data)

