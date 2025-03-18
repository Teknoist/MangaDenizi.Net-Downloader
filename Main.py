import os
import sys
import shutil
import asyncio
import aiohttp
import zipfile
import requests
from bs4 import BeautifulSoup
from lxml import html

# ANSI renk kodları (terminal renkleri)
COLOR_GREEN = "\033[1;32m"
COLOR_BLUE = "\033[1;34m"
COLOR_RED = "\033[1;31m"
COLOR_RESET = "\033[0m"

# AYARLAR:
MAX_CONCURRENT_DOWNLOADS = 10  # Aynı anda indirilebilecek resim sayısı

# URL'den başlaması gereken tüm bölüm linklerini toplayan fonksiyon
def get_all_links(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = set()
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith(url):
                # URL'nin sonundaki '/' kaldırılıp '/1' ekleniyor (sayfa numarası)
                full_link = href.rstrip('/') + '/1'
                links.add(full_link)
        return links
    except Exception as e:
        print(f"{COLOR_RED}❌ get_all_links fonksiyonunda hata: {e}{COLOR_RESET}")
        return set()

# URL'leri bölüm numarasına göre sıralayan fonksiyon
def sort_urls(urls):
    def extract_chapter_number(url):
        try:
            # Örnek URL: https://www.mangadenizi.net/manga/relife/051.5/1 → bölüm numarası: 51.5
            parts = url.strip().rstrip('/').split('/')
            chapter_str = parts[-2]
            return float(chapter_str)
        except Exception as e:
            print(f"{COLOR_RED}❌ URL sıralama hatası: {e}{COLOR_RESET}")
            return float('inf')
    return sorted(urls, key=extract_chapter_number)

# Belirtilen klasördeki dosyaları zipleyip .cbz olarak kaydeden fonksiyon
def create_cbz(source_dir, output_filename):
    try:
        with zipfile.ZipFile(output_filename, 'w') as cbz:
            # Dosyaları sıralı bir şekilde arşive ekliyoruz
            for root, _, files in os.walk(source_dir):
                for file in sorted(files):
                    file_path = os.path.join(root, file)
                    cbz.write(file_path, arcname=file)
        print(f"{COLOR_GREEN}📦 CBZ oluşturuldu: {output_filename}{COLOR_RESET}")
    except Exception as e:
        print(f"{COLOR_RED}❌ CBZ oluşturulurken hata: {e}{COLOR_RESET}")

# Asenkron olarak tek bir resmin indirilip kaydedildiği ve yeniden denendiği fonksiyon
async def download_image(session, url, save_path, semaphore, max_retries=3):
    async with semaphore:
        for attempt in range(1, max_retries + 1):
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        with open(save_path, 'wb') as f:
                            f.write(content)
                        print(f"{COLOR_GREEN}✅ {os.path.basename(save_path)} indirildi! (Deneme {attempt}){COLOR_RESET}")
                        return True  # Başarılı indirme
                    else:
                        print(f"{COLOR_RED}❌ {os.path.basename(save_path)} HTTP {resp.status} ile indirilemedi (Deneme {attempt}).{COLOR_RESET}")
            except Exception as e:
                print(f"{COLOR_RED}❌ {os.path.basename(save_path)} indirilirken hata: {e} (Deneme {attempt}){COLOR_RESET}")
            # Denemeler arasında 1 saniye bekle
            await asyncio.sleep(1)
        return False  # Tüm denemeler başarısız

# Bir bölümün HTML sayfasını asenkron olarak çekip, resim linklerini ayrıştıran fonksiyon
async def fetch_chapter_data(chapter_url, session):
    try:
        async with session.get(chapter_url) as resp:
            if resp.status != 200:
                print(f"{COLOR_RED}❌ {chapter_url} sayfası HTTP {resp.status} ile açılamadı.{COLOR_RESET}")
                return None, []
            html_text = await resp.text()
            tree = html.fromstring(html_text)
            xpath_expression = '//img[@class="img-responsive"]/@data-src'
            raw_image_links = tree.xpath(xpath_expression)
            image_links = [
                ('https:' + link.strip()) if link.strip().startswith("//") else link.strip()
                for link in raw_image_links
            ]
            # Bölüm adını URL'den alıyoruz (sondan bir önceki kısım)
            chapter_name = chapter_url.rstrip('/').split('/')[-2]
            print(f"{COLOR_BLUE}🔍 {chapter_name} bölümü alındı. ({len(image_links)} resim){COLOR_RESET}")
            return chapter_name, image_links
    except Exception as e:
        print(f"{COLOR_RED}❌ {chapter_url} bölüm verisi alınırken hata: {e}{COLOR_RESET}")
        return None, []

# Bir bölümü indirip, eksik resimler varsa temizleyerek yeniden denemeye çalışan fonksiyon.
async def process_chapter(chapter_name, image_links, max_chapter_retries=3):
    expected_count = len(image_links)
    for attempt in range(1, max_chapter_retries + 1):
        # Geçici klasör: her deneme için ayrı bir klasör kullanıyoruz
        chapter_temp_dir = os.path.join("chapters", f"{chapter_name}_temp")
        os.makedirs(chapter_temp_dir, exist_ok=True)
        print(f"{COLOR_BLUE}🚀 {chapter_name} indiriliyor... (Deneme {attempt}/{max_chapter_retries}){COLOR_RESET}")

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
        connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_DOWNLOADS * 2)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for idx, url in enumerate(image_links, start=1):
                file_ext = url.split('.')[-1] if '.' in url else 'jpg'
                filename = f"{idx:03d}.{file_ext}"
                save_path = os.path.join(chapter_temp_dir, filename)
                task = asyncio.create_task(download_image(session, url, save_path, semaphore, max_retries=3))
                tasks.append(task)
            await asyncio.gather(*tasks)

        # İndirme tamamlandıktan sonra, inen dosya sayısını kontrol ediyoruz.
        downloaded_files = [
            f for f in os.listdir(chapter_temp_dir)
            if os.path.isfile(os.path.join(chapter_temp_dir, f))
        ]
        actual_count = len(downloaded_files)

        if actual_count == expected_count:
            print(f"{COLOR_GREEN}✅ {chapter_name} bölümü tamamlandı. {actual_count}/{expected_count} resim indirildi.{COLOR_RESET}")
            cbz_filename = os.path.join("chapters", f"{chapter_name}.cbz")
            create_cbz(chapter_temp_dir, cbz_filename)
            shutil.rmtree(chapter_temp_dir)
            return True
        else:
            print(f"{COLOR_RED}⚠ {chapter_name} bölümünde sorun: {actual_count} resim indirildi, {expected_count} bekleniyordu. Yeniden deneniyor...{COLOR_RESET}")
            shutil.rmtree(chapter_temp_dir)
    print(f"{COLOR_RED}❌ {chapter_name} bölümü için maksimum deneme sayısına ulaşıldı. Bu bölüm indirilemedi.{COLOR_RESET}")
    return False

# Tüm bölümlerin verilerini asenkron olarak çekmek için görev oluşturan fonksiyon
async def fetch_all_chapter_data(chapter_urls):
    chapters_data = []
    connector = aiohttp.TCPConnector(limit=50)  # Bölüm çekme işlemlerinde eşzamanlılık limiti artırıldı
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_chapter_data(url, session) for url in chapter_urls]
        results = await asyncio.gather(*tasks)
        for chapter_name, image_links in results:
            if chapter_name is not None and image_links:
                chapters_data.append((chapter_name, image_links))
    return chapters_data

# Ana asenkron fonksiyon: Tüm işlemleri organize eder
async def main():
    if len(sys.argv) != 2:
        print(f"{COLOR_BLUE}Kullanım: python script.py <URL>{COLOR_RESET}")
        sys.exit(1)

    base_url = sys.argv[1]
    manga_adi = base_url.rstrip('/').split('/')[-1]
    print(f"{COLOR_BLUE}📖 {manga_adi} için indirme işlemi başlatılıyor...{COLOR_RESET}")

    # Bölüm URL'lerini çekiyoruz
    all_links = get_all_links(base_url)
    if not all_links:
        print(f"{COLOR_RED}❌ Hiçbir bölüm bulunamadı!{COLOR_RESET}")
        sys.exit(1)

    # URL'leri bölüm numarasına göre sıralıyoruz
    sorted_links = sort_urls(all_links)

    # Tüm bölümlerin veri çekme işlemini asenkron olarak gerçekleştiriyoruz
    chapters_data = await fetch_all_chapter_data(sorted_links)
    if not chapters_data:
        print(f"{COLOR_RED}❌ Hiçbir bölüm verisi alınamadı!{COLOR_RESET}")
        sys.exit(1)

    # "chapters" klasörünü oluşturuyoruz (varsa kullanılır)
    os.makedirs("chapters", exist_ok=True)

    # Her bölümü asenkron olarak işle
    tasks = [process_chapter(chapter_name, image_links) for chapter_name, image_links in chapters_data]
    await asyncio.gather(*tasks)

    # Tüm CBZ dosyaları "chapters" klasöründe oluşturulduktan sonra, manganın adıyla bir klasör oluşturup oraya taşıyoruz.
    manga_klasoru = manga_adi  # Örneğin, "relife"
    os.makedirs(manga_klasoru, exist_ok=True)
    for file in os.listdir("chapters"):
        if file.endswith(".cbz"):
            src_path = os.path.join("chapters", file)
            dest_path = os.path.join(manga_klasoru, file)
            shutil.move(src_path, dest_path)

    print(f"{COLOR_GREEN}🏁 {manga_adi} başarıyla indirildi. Tüm CBZ dosyaları '{manga_klasoru}' klasöründe saklanıyor.{COLOR_RESET}")

if __name__ == "__main__":
    asyncio.run(main())
