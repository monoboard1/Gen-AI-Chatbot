import voyageai
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
import seaborn as sns

# Use Voyage AI API KEY
api_key = "<YOUR_VOYAGE_AI_API_KEY_HERE>"

vo = voyageai.Client(api_key=api_key)
# This will automatically use the environment variable VOYAGE_API_KEY.
# Alternatively, you can use vo = voyageai.Client(api_key="<your secret key>")

result = vo.embed(["hello world"], model="voyage-large-2")
# Set a distinct number of drug categories
distinct_drug_categories = [
    'Analgesics',
    'Antibiotics',
    'Antifungal Agents',
    'Antiviral Agents',
    'Antipyretics',
    'Antiseptics',
    'Mood Stabilizers',
    'Anti-Inflammatory Agents',
    'Anticoagulants',
    'Antihistamines',
    'Diuretics',
    'Laxatives',
    'Bronchodilators',
    'Anticonvulsants',
    'Antidepressants'
]

def embed_vector(list_of_text):
    list_of_text: list
    if type(list_of_text) == list:
        result = vo.embed(list_of_text, model="voyage-large-2")
    else:
        print("The input must be a list")
        return TypeError
    return result.embeddings

def best_drug_category(categories, standard_list):
    vecs = embed_vector([categories]+standard_list)
    vec_array = np.array(vecs)

    # Calculate cosine similarity
    similarity_matrix = cosine_similarity(vec_array)

    first_line_similarities = similarity_matrix[0, 1:]

    # Find the index of the highest similarity
    best_fit_index = np.argmax(first_line_similarities)

    # Get the corresponding category
    best_fit_category = distinct_drug_categories[best_fit_index]

    return best_fit_category

def plot_variance_distribution(data):
    plt.figure(figsize=(8, 6))
    sns.histplot(data, bins=20, kde=True)
    plt.title('Distribution of Variance Values (without self-similarity)')
    plt.xlabel('Variance')
    plt.ylabel('Frequency')
    plt.show()
    return True

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# Base URL for DrugBank
base_url = "https://go.drugbank.com/drugs/"

# Range of DrugBank IDs to scrape
start_id = 1000
end_id = 1500  # Example range, adjust as needed

# Initialize a list to store drug data
drugs_data = []

for i in range(start_id, end_id + 1):
    drug_id = f"DB{i:05d}"
    url = f"{base_url}{drug_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract the drug ID
        drug_id_meta = soup.find('meta', attrs={'name': 'dc.identifier'})
        drug_id_value = drug_id_meta['content'] if drug_id_meta else 'N/A'
        
        # Extract the drug name
        drug_name_meta = soup.find('meta', attrs={'name': 'dc.title'})
        drug_name = drug_name_meta['content'] if drug_name_meta else 'N/A'
        
        # Extract the drug description
        description_meta = soup.find('meta', attrs={'name': 'description'})
        description = description_meta['content'] if description_meta else 'N/A'
        
        # Extract additional fields by looking for dt/dd pairs
        def get_text_for_label(label):
            tag = soup.find('dt', text=label)
            if tag:
                next_tag = tag.find_next_sibling('dd')
                if next_tag:
                    return next_tag.text.strip()
            return 'N/A'

        # Data to collect
        mechanism_of_action = get_text_for_label('Mechanism of action')
        indication = get_text_for_label('Indication')
        pharmacodynamics = get_text_for_label('Pharmacodynamics')
        absorption = get_text_for_label('Absorption')
        volume_of_distribution = get_text_for_label('Volume of distribution')
        protein_binding = get_text_for_label('Protein binding')
        metabolism = get_text_for_label('Metabolism')
        drug_categories = get_text_for_label('Drug Categories')

        # Append the data to the list
        drugs_data.append({
            'DrugBank ID': drug_id_value,
            'Name': drug_name,
            'Description': description,
            'Mechanism of Action': mechanism_of_action,
            'Indication': indication,
            'Pharmacodynamics': pharmacodynamics,
            'Absorption': absorption,
            'Volume of Distribution': volume_of_distribution,
            'Protein Binding': protein_binding,
            'Metabolism': metabolism,
            'Drug Categories': drug_categories,
            # Add more fields as necessary
        })
        print(f"Gathered data for {drug_id}")
        # Just so not to overwhelm the server 
        time.sleep(0.01)
    else:
        print(f"Failed to retrieve data for {drug_id}")

# Convert the list to a pandas DataFrame
df = pd.DataFrame(drugs_data)