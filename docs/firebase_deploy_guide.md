# Firebase Hosting — Deploy заавар (𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 вэбсайт)

## Таны одоогийн төлөв ✅

Таны Firebase Hosting аль хэдийн тохируулагдсан байна:

| Зүйл | Утга |
|---|---|
| Firebase төсөл | `aether-c1915` (`.firebaserc`-д бичигдсэн) |
| Deploy хавтас | `website/` (`firebase.json`-д заасан) |
| Live URL | https://aether-c1915.web.app (200 OK баталгаажсан) |
| Cache | Зурган файл 1 жил, JS/CSS 1 өдөр (зөв тохируулсан) |

## Гол анхаарах зүйл: шинэ лого Firebase дээр харагдах үү?

Хамгийн сүүлийн commit (`2c77cc7` — шинэ AETHER neon лого) GitHub-д явсан ч **Firebase руу өөрөө deploy хийгдэхгүй**. Учир нь Firebase Hosting-ийн deploy нь GitHub Actions эсвэл `firebase deploy` коммандоор гар аргаар хийгддэг — пуш хийхэд автоматаар явахгүй байсан.

Тэгэхээр **одоо Firebase дээр хуучин лого л байна** — GitHub Pages (`zero1zx1.github.io/Vortex`) л шинэ лого руу солигдсон.

## Шинэ логог Firebase-д явуулах 2 арга

### Арга 1: Локал дээрээс deploy (одоохондоо)

Windows PowerShell дээр:

```powershell
cd C:\Users\hotar\OneDrive\Desktop\Vortex
firebase deploy --only hosting
```

Firebase CLI суугаагүй бол:

```powershell
npm install -g firebase-tools
firebase login
firebase deploy --only hosting
```

Энэ нь `aether-c1915` төсөл рүү `website/` хавтсыг шууд явуулна. Гарах үр дүн:

```
✔ Deploy complete!
Hosting URL: https://aether-c1915.web.app
```

### Арга 2: GitHub Actions — автоматаар (би бэлдлээ)

`firebase-hosting.yml` workflow файлыг репод нэмлээ. Гэхдээ энэ ажиллахын тулд **Firebase service account secret**-ыг GitHub руу нэмэх шаардлагатай:

1. Firebase Console руу ор: https://console.firebase.google.com/project/aether-c1915/settings/serviceaccounts/adminsdk
2. **"Generate new private key"** дарж JSON файл татаж авах
3. GitHub → ZERO1zx1/Vortex → **Settings → Secrets and variables → Actions → New repository secret**
4. Secret нэр: `FIREBASE_SERVICE_ACCOUNT_AETHER_C1915`
5. JSON файлын **бүх агуулгыг** (нэг мөрөөр) тэнд нааж хадгалах

Үүний дараа main-д пуш хийх бүр сайт автоматаар Firebase руу deploy хийгдэнэ.

## Firebase vs GitHub Pages — хоёулаа ажиллана

- https://zero1zx1.github.io/Vortex/ — GitHub Pages (commit пуш бүрэд автоматаар)
- https://aether-c1915.web.app — Firebase Hosting (workflow тохируулсны дараа автоматаар)

Хоёр линкээр хандаж болно; аль нэгийг нь community линк болгон сонгоод хангалттай.
