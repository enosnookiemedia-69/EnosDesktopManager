from pathlib import Path

# Main Book folder
book_folder = Path(r"C:\Enos Desktop Manager\Book")

# Enos Nookie book categories
categories = [
    "Setup & Workshop",
    "Build Onsite",
    "Jollers & People",
    "Artworks & Burns",
    "Landscapes & Nature",
    "Nightlife & DJs",
    "Strike & Packing",
    "Portraits & Extras",
    "Cover",
    "Where's Enos",
]

print("Enos Nookie - Book Folder Setup")
print("=" * 35)

# Make sure the Book folder exists
book_folder.mkdir(parents=True, exist_ok=True)

# Create each category folder
for category in categories:
    folder = book_folder / category
    folder.mkdir(exist_ok=True)
    print(f"Created: {folder}")

print()
print("Done!")
