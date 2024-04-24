# MangaDenizi.Net-İndirici

Bu basit Python betiği, MangaDenizi.Net web sitesinden mangaları otomatik olarak indirmenize ve dönüştürmenize olanak sağlar. Sadece birkaç adımda istediğiniz mangayı PDF formatında kaydedebilirsiniz.

## Nasıl Kullanılır

1. Öncelikle, bilgisayarınızda Python yüklü olmalıdır. Eğer yüklü değilse [Python'un resmi web sitesinden](https://www.python.org/downloads/) indirebilir ve kurabilirsiniz.

2. Gerekli modülleri yüklemek için terminal veya komut istemcisini açın ve aşağıdaki komutları girin:

    ```
    pip install fpdf Pillow beautifulsoup4
    ```

3. Şimdi, `Main.py` dosyasını indirin veya klonlayın.

4. Terminal veya komut istemcisinde aşağıdaki komutu kullanarak betiği çalıştırın:

    ```
    python ./Main.py [MANGA_URL]
    ```

    `[MANGA_URL]` kısmını indirmek istediğiniz manganın MangaDenizi.Net'teki URL'si ile değiştirin. Örneğin:

    ```
    python ./Main.py https://www.mangadenizi.net/manga/0c-magic
    ```

5. Betik, manga bölümlerini indirecek ve PDF formatına dönüştürecektir. İşlem tamamlandığında, çalışma dizininizde `Manga` adında bir klasör oluşturulacaktır. Bu klasörü açarak indirdiğiniz manganın bölümlerini görüntüleyebilirsiniz.

## Gereksinimler

- Python 3.x
- FPDF
- Pillow
- BeautifulSoup4
