# NovelBin Downloader
Este é um script para baixar as novels do site NovelBin, já traduzindo os capítulos no processo, salvando no formato .docx

```bash
apt install wget -y
wget https://raw.githubusercontent.com/luanwillianzh/novelbin_downloader/refs/heads/novelbin
chmod +x novelbin
mv novelbin $PREFIX/bin/
termux-setup-storage
echo "Para baixar novel só digitar o comando 'novelbin'"
```
