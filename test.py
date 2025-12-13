import json
import os

def fix_swapped_fields(file_path):
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    try:
        # Read the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        corrected_count = 0
        
        for item in data:
            # Get current values, defaulting to empty string if missing
            current_tag = item.get('tag', '').strip()
            current_category = item.get('category', '').strip()
            
            # Comparison logic:
            # If the tag is NOT 'SALESFORCE' (case-insensitive), we assume it's swapped.
            if current_tag.upper() != 'SALESFORCE':
                
                # Perform the swap
                item['tag'] = current_category
                item['category'] = current_tag
                
                # Update the tag variable for the next check
                current_tag = item['tag']
                corrected_count += 1

            # Standardization:
            # If the tag is now "Salesforce" (mixed case), force it to "SALESFORCE"
            # to match the rest of your file.
            if item.get('tag', '').upper() == 'SALESFORCE':
                item['tag'] = 'SALESFORCE'

        # Write the corrected data back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"Success! Processed {len(data)} items.")
        print(f"Corrected {corrected_count} items where tag and category were swapped.")

    except json.JSONDecodeError:
        print("Error: The file is not valid JSON.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # You can change the filename here if it is different
    fix_swapped_fields('mcqs.json')