import requests
url = "https://github.com/cyrealtype/Lora-Cyrillic/raw/master/fonts/ttf/Lora-Regular.ttf"
r = requests.get(url)
with open("lora.ttf", "wb") as f:
    f.write(r.content)
print("done", len(r.content))
