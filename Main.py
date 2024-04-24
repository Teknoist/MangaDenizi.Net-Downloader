import os
import sys
import requests
from bs4 import BeautifulSoup
from lxml import html
from PIL import Image
from fpdf import FPDF
import shutil

# Verilen URL'den başlayan tüm linkleri alacak fonksiyon
def get_all_links(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    links = set()
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.startswith(url):
            href += '/1'
            links.add(href)
    return links

# Function to download images from URLs in a text file
def download_images_from_txt(txt_file):
    with open(txt_file, 'r') as file:
        lines = file.readlines()
        for line in lines:
            url = line.strip()
            filename = url.split('/')[-1]
            response = requests.get(url)
            if response.status_code == 200:
                os.makedirs("down", exist_ok=True)
                with open(os.path.join("down", filename), 'wb') as img_file:
                    img_file.write(response.content)
                print(f"Downloaded {filename}")
            else:
                print(f"Failed to download {filename}")

# Function to merge downloaded images into a PDF
def merge_images_to_pdf(txt_file):
    pdf = FPDF()
    with open(txt_file, 'r') as file:
        lines = file.readlines()
        for line in lines:
            filename = line.strip().split('/')[-1]
            filepath = os.path.join("down", filename)
            if os.path.exists(filepath):
                pdf.add_page()
                pdf.image(filepath, 0, 0, 210, 297)
                print(f"Added {filename} to PDF")
    pdf_output = os.path.join("down", os.path.splitext(os.path.basename(txt_file))[0] + '.pdf')
    pdf.output(pdf_output, "F")
    print(f"PDF created: {pdf_output}")
    delete_images_in_folder("down")

# Function to delete all files with a specified extension in a folder
def delete_images_in_folder(folder):
    for file in os.listdir(folder):
        if file.endswith(".jpg"):
            os.remove(os.path.join(folder, file))
            print(f"Deleted {file}")

# Main function
def main():
    if len(sys.argv) != 2:
        print("Kullanım: python script.py <URL>")
        sys.exit(1)
    url = sys.argv[1]
    manga = sys.argv[1].split('/')[-1]
    print(manga)
    all_links = get_all_links(url)
    file_name = "urls.txt"
    with open(file_name, 'w') as file:
        for link in all_links:
            file.write(link + '\n')
    print(f'Tüm linkler {file_name} dosyasına kaydedildi.')
    
    with open('urls.txt', 'r') as link_file:
        urls = link_file.readlines()
    for url in urls:
        url = url.strip()
        response = requests.get(url)
        tree = html.fromstring(response.content)
        xpath_expression = '//img[@class="img-responsive"]/@data-src'
        image_links = tree.xpath(xpath_expression)
        fixed_image_links = ['https:' + link.strip() for link in image_links]
        directory = 'src'
        if not os.path.exists(directory):
            os.makedirs(directory)
        file_name = url.split('/')[-2] + '.txt'
        file_path = os.path.join(directory, file_name)
        with open(file_path, 'w') as file:
            for link in fixed_image_links:
                file.write(link + '\n')
    
    folder_path = "src"
    txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
    for txt_file in txt_files:
        download_images_from_txt(os.path.join(folder_path, txt_file))
        merge_images_to_pdf(os.path.join(folder_path, txt_file))
            
    shutil.rmtree("src")
    os.remove("urls.txt")
    man = "./" + manga
    print(f"{man} İndirildi")
    shutil.move("./down", manga)

if __name__ == "__main__":
    main()
