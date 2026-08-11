# F1 1:43 Model Catalog - projektovy dokument

Posledni aktualizace: 2026-08-11

Tento soubor je zivy projektovy dokument. Pri kazde vetsi zmene aplikace, datove logiky, importu, pravidel parovani nebo cloudove architektury se ma aktualizovat. Ma slouzit jako hlavni brief pro GitHub, dalsi vyvoj a pozdejsi cloudove nasazeni.

## Cil projektu

Cilem je cloudova aplikace pro katalog a sbirku modelu Formule 1 v meritku 1:43.

Aplikace musi umet:

- vytvorit nezavisly master katalog vsech znamych vyrobenych F1 1:43 modelu,
- u kazdeho modelu drzet katalogove udaje, zdroje a fotografie,
- porovnat master katalog s osobni sbirkou az jako posledni krok,
- zobrazit roky, katalog, sbirku, kandidaty k overeni a detail jednoho modelu,
- rozlisit stav modelu barvou radku: ve vitrine, mimo vitrinu, chybi, NO MODEL,
- prubezne rozsirovat katalog dalsimi roky a vyrobci.

Zasadni pravidlo: osobni tabulka sbirky neni zdroj pravdy pro to, co existuje. Slouzi pouze k finalnimu porovnani, co z master katalogu uz je ve sbirce.

## Aktualni datovy stav

Aktualni aplikacni data jsou v:

- `app/data/app-data.json`
- `app/data/model_photo_overrides.json`

Aktualni souhrn po poslednim prepoctu:

- master katalog: 3176 modelu,
- kandidati k overeni: 893 zaznamu,
- radky sbirky: 2721,
- vlastnene radky sbirky: 2388,
- unikatni vlastnene katalogove kody: 2218,
- zdrojove radky pred striktni filtraci katalogu: 5034.

Stav pilotnich rocniku:

- 1979: sbirka 46 radku, vlastneno 38, master modely 63, modely s fotkou 63, radky sbirky s fotkou 45.
- 1980: sbirka 57 radku, vlastneno 47, master modely 26, modely s fotkou 24, radky sbirky s fotkou 44.
- 1981: sbirka 58 radku, vlastneno 44, master modely 58, modely s fotkou 56, radky sbirky s fotkou 47.

Poznamka: cisla se budou menit s doplnovanim dalsich zdroju a oprav.

## Zakladni architektura dat

Projekt ma dve oddelene roviny:

1. Master katalog
   - popisuje, co bylo vyrobeno,
   - vznikne nezavisle z vyrobcu, prodejcu, aukci, for a katalogu,
   - nesmi byt generovan z osobni sbirky.

2. Osobni sbirka
   - popisuje, co vlastnik ma,
   - pouziva se az ve finalnim porovnani proti master katalogu,
   - muze obsahovat vlastni zapisy, preklepy, prodejni kody, chybejici vyrobce nebo ruzne varianty jmen.

Master katalog je zdroj pravdy pro existenci modelu. Sbirka je zdroj pravdy pro vlastnictvi.

## Datovy model master katalogu

Kazdy model v master katalogu ma mit minimalne tato pole:

- `Year`
- `Constructor/Car`
- `Chassis/Type`
- `Driver`
- `Car number`
- `Team/livery`
- `Race/GP/version`
- `Manufacturer`
- `Model code`
- `Scale`
- `Source URL`
- `Source name`
- `Raw source title`
- `Limited edition`
- `Notes`
- `Main photo`
- `Thumbnails`
- `Photo source URL`
- `Match status against collection`

V aplikaci se tato data prepisuji do JSON struktury v `app-data.json`.

## Datovy model sbirky

Hlavnim vstupem osobni sbirky je soukromy Excel workbook. V public GitHub repozitari se tento soubor nesmi commitovat.

Lokalni pracovni cesta muze byt v `outputs/`, ale tato slozka je pro public repo ignorovana.

List: `Overview`

Sloupce:

- `Year`
- `Team`
- `Car`
- `Type`
- `Nr`
- `Driver`
- `Brand`
- `Extra`
- `D` = poradi jezdce v sampionatu,
- `DP` = body jezdce,
- `T` = poradi tymu/konstruktera,
- `TP` = body tymu/konstruktera,
- `Pc` = pocet modelu; od roku 1990 znamena `Pc=0`, ze model neni ve sbirce,
- `Code`
- `NV` = neni ve vitrine,
- `V` = je ve vitrine.

Pri doplnovani do Excelu se musi zachovat formatovani. Hyperlink v bunce ma zobrazovat nazev, ne URL.

## Zasadni pravidla importu roku

Funkce pro dalsi rok ma fungovat takto:

1. Uzivatel zada rok.
2. System vytvori nezavisly master katalog pro tento rok.
3. System vyhleda modely u relevantnich vyrobcu a prodejcu.
4. System normalizuje kody a vyhodi ne-F1 zaznamy.
5. System dohleda a overi fotografie.
6. System slouci duplicity.
7. System vygeneruje audit kvality.
8. Teprve potom system porovna master katalog s osobni sbirkou.
9. System prepocita `app-data.json`.
10. System overi aplikaci v prohlizeci.

Osobni tabulka se nesmi pouzivat jako seed pro existenci modelu. Vyjimka: muze se pouzit jen jako seznam veci k finalnimu porovnani a jako upozorneni, ze nekde muze chybet model v master katalogu.

## Navrhovany prikaz pro rocni import

Cilovy prikaz:

```powershell
python app/scripts/build_year.py --year 1981
```

Interni kroky prikazu:

```text
collect_year_sources(year)
normalize_catalog_rows(year)
validate_catalog_codes(year)
remove_non_f1_rows(year)
merge_duplicates(year)
discover_and_verify_photos(year)
match_catalog_against_collection(year)
build_app_data()
run_browser_smoke_test(year)
write_year_audit(year)
```

Tento prikaz zatim neni hotovy jako jeden soubor. Existuji dilci skripty, ktere je potreba sjednotit.

## Existujici skripty

Koren projektu:

- `audit_f1_wiki.py` - audit kombinaci jezdec/tym podle Wikipedie.
- `build_diecast_audit_version.py` - vytvoreni doplnene verze Excelu.
- `repair_diecast_hyperlinks.py` - oprava hyperlinku v Excelu, aby bunka zobrazovala nazev.
- `fill_diecast_standings_points.py` - doplneni poradi a bodu 1976-2025.
- `collect_model_catalog.py` - starsi sber katalogu.
- `collect_model_catalog_expanded.py` - rozsireny sber katalogu.
- `match_model_catalog.py` - parovani master katalogu proti sbirce.
- `catalog_rules.py` - sdilena pravidla kodu, vyrobcu a non-F1 filtru.
- `build_model_catalog_workbook.mjs` - export katalogu do workbooku.

Aplikace:

- `app/scripts/import_spark_official_f1.py` - import oficialniho Spark katalogu pro rok.
- `app/scripts/import_143diecast_minichamps.py` - import 143diecast/Minichamps stranek.
- `app/scripts/discover_model_photos.py` - hledani a extrakce fotek z produktovych stranek.
- `app/scripts/import_collection_catalog_seed.py` - pomocny import ze sbirky; nesmi byt hlavni zdroj master katalogu.
- `app/scripts/prepare_app_data.py` - sestaveni `app-data.json`.
- `app/serve_app.py` - stabilni lokalni server pro aplikaci bez problemu s logovanim.

## Pravidla vyrobcu a katalogovych kodu

### Spark

Platny kanonicky Spark kod je pouze:

```text
S1234
```

Prijatelne vstupy pro normalizaci:

- `S1234`
- `SP1234`
- `SPK1234`
- `SPK 1234`

Vse se uklada jako `S1234`.

Dulezite zkusenosti:

- Raceland ma vlastni prodejni kody typu `20-41757`; ty nejsou Spark kody.
- Prodejni kod se smi ulozit jako zdroj nebo pomocny odkaz, ale nesmi se prepsat na Spark `Sxxxx`, pokud se realny Spark kod neprokaze jinym zdrojem.
- Predchozi chybna logika omylem mapovala nektere Raceland kody na Spark kody, coz mohlo vytvaret spatne shody.
- U `S9303` ve sbirce bylo nutne pouzit fotku z realneho Spark kodu `S3903`; toto je konkretni vyjimka/foto alias, ne obecne pravidlo.

### Minichamps

Platny Minichamps kod je 9 cislic:

```text
430790027
```

Prijatelne vstupy:

- `430790027`
- `430 790027`
- `430-790027`

Vse se uklada jako 9 cislic bez mezer.

Dulezite zkusenosti:

- Ne vsechny 9mistne kody ve stocklistech jsou F1.
- F1 Scale Models stocklist obsahoval i non-F1 priklady jako Ralt Toyota RT3 nebo Van Diemen RF81; ty se musi vyhazovat non-F1 filtrem.
- U Minichamps se nesmi spolehat jen na jeden stocklist. Je potreba kontrolovat vice zdroju vcetne oficialnich stranek a prodejcu.

### Ostatni vyrobci

Relevantni vyrobci a znacky:

- Spark
- Minichamps
- LookSmart
- Hot Wheels
- TSM
- Quartzo
- Onyx
- Ebbro
- Tameo
- BBR
- GP Replicas
- Altaya
- Ixo
- Brumm
- CP Model
- Volare Brasil
- Planex
- dalsi, pokud se prokazi jako relevantni F1 1:43

Kazdy vyrobce muze mit vlastni pravidlo kodu. Dokud pravidlo neexistuje, kod se zachovava opatrne a jde do kandidatu k overeni, pokud neni jednoznacny.

## Non-F1 filtr

Z katalogu se musi vyhazovat:

- Formula 2,
- F2,
- Formula 3,
- F3,
- Formula Ford,
- IndyCar,
- CART,
- Indy 500,
- Le Mans,
- sportscar,
- GT,
- DTM,
- touring cars,
- Ralt Toyota RT3,
- Van Diemen RF81.

Toto pravidlo je v `catalog_rules.py` a musi se pouzivat ve vsech importech.

## Pravidla fotek

Fotka neni validni jen proto, ze existuje URL v datech.

Fotka je validni az kdyz:

- URL vrati HTTP 200,
- `Content-Type` je obrazek,
- obrazek neni placeholder,
- obrazek odpovida modelu nebo presne stavebnici/verzi,
- zdroj URL je ulozen v modelu.

Preferovane poradi zdroju fotek:

1. oficialni stranka vyrobce,
2. specializovany prodejce modelu,
3. aukcni/prodejni stranka s presnym modelem,
4. forum nebo katalogova databaze,
5. rucne pridany overeny link.

Nesmime davat fotku skutecneho auta misto fotky modelu, pokud model existuje a jde dohledat.

## Zkusenost: Spark CDN problem

Oficialni Spark API vraci obrazky z:

```text
https://minimax.fra1.cdn.digitaloceanspaces.com/...
```

Tyto obrazky se v datech tvari jako platne, ale pri hotlinku z aplikace nebo pri overeni vraci casto:

```text
403 Forbidden
```

Oprava pouzita pro rok 1979:

- rozbite Spark `minimax` odkazy byly nahrazeny funkcni URL z DiecastLegends ve tvaru:

```text
https://www.diecastlegends.com/Images/Product/Default/xlarge/SPK1734_1.jpg
```

- po nahrade bylo overeno 23/23 Spark radku pro 1979,
- vsechny vratily `200 image/jpeg`,
- detail `S1734 Tyrrell-Ford 009 Didier Pironi` byl overen v prohlizeci.

Do budouci logiky patri automaticky fallback:

```text
Spark API URL -> overit -> pokud 403, hledat DiecastLegends/GrandPrixModels/Raceland/CK/Carmodel
```

## Zkusenost: Volare Brasil a blokovane weby

Nektere weby blokovaly primy pristup nebo API:

- Volare Brasil vracel 403,
- MercadoLivre vyzadoval prihlaseni nebo blokoval API.

Funkcni alternativa:

- JVL Classics melo aukcni stranky s presnym modelem a velkymi fotkami.

Pro 1979 byly takto doplneny:

- Volare Brasil Fittipaldi F6A Emerson Fittipaldi, German GP,
- Volare Brasil Fittipaldi F6A Alex Ribeiro, Canadian GP.

## Zkusenost: Tameo, CP Model, GP Cars Model

Pro 1979 byly pouzity specializovane zdroje:

- Tameo TWU 003 Wolf WR7 USA West GP / Monaco GP 1979,
- Vendilo Segrate jako druhy zdroj Tameo Wolf WR7,
- GP Cars Model pro CP Model Merzario A1B.

U techto typu modelu muze jit o stavebnici nebo hand-built. Je nutne rozlisovat:

- model existuje,
- model existuje jako kit,
- model existuje jako hand-built,
- model nema potvrzenou 1:43 podobu.

## Zkusenost: radky bez modelu

Pokud je radek ve sbirce zluty a model neni potvrzeny, nesmi se mu davat nahodna fotka podobneho auta.

Priklad 1979:

- `Tyrrell-Ford 009 / Derek Daly` zustal bez fotky, protoze nebyl potvrzen presny existujici 1:43 model pro dany zaznam.

Toto je spravne chovani. Lepsi je prazdny radek nez spatna fotka.

## Logika parovani katalogu se sbirkou

Porovnani se sbirkou probiha az po sestaveni master katalogu.

Poradi parovani:

1. Presny katalogovy kod + vyrobce.
2. Alias kodu, pokud je pravidlo explicitne povolene.
3. Rok + vyrobce + sasi + jezdec + cislo.
4. Rok + sasi + jezdec + GP/detail.
5. Pravdepodobna shoda do kandidatu.
6. Nenalezeno.

Jmena jezdcu se musi normalizovat:

- `Schumacher Michael` vs `Michael Schumacher`,
- diakritika,
- iniciály,
- `Sainz Carlos jr`,
- ruzne mezery a pomlcky.

Texty aut a tymu se musi normalizovat:

- mezery,
- pomlcky,
- `Ford Cosworth` vs `Ford`,
- zkratky GP,
- jazykove varianty `British GP` / `UK GP` / `Grand Prix of Great Britain`.

## Stav radku ve sbirce

Barvy:

- zelena = model je ve vitrine (`V > 0`),
- bila = model je ve sbirce, ale mimo vitrinu (`Pc > 0` nebo `NV > 0`, `V = 0`),
- zluta = model chybi (`Pc = 0`, neni NO MODEL),
- cervena = `NO MODEL`.

Sloupec `V/NV` ma zobrazovat pouze:

- `V`,
- `NV`,
- prazdno.

Textovy sloupec `Stav` vpravo byl odstraneny. Stav ma byt vyjadren podbarvenim radku.

## UI logika aplikace

Soucasna aplikace je staticka webova aplikace:

- `app/index.html`
- `app/src/app.js`
- `app/src/styles.css`
- `app/data/app-data.json`
- `app/assets/model-placeholder.svg`

Pohledy:

- `Sbírka`
- `Přehled`
- `Roky`
- `Katalog`
- `Kandidáti`

Vychozi prvni tlacitko je `Sbírka`.

Horni stavovy radek:

- hledani,
- rok,
- vyrobce,
- sbirka,
- stav,
- statistiky radku/kusu/V/NV,
- tlacitko vycistit,
- tlacitko obnovit data.

Levy detail:

- hlavni fotka modelu,
- thumbnaily dalsich fotek vedle hlavni fotky,
- informace pod obrazkem ve stylu:

```text
1979 Spark Ensign Ford N180 G.Lees #41; 1979, Dutch GP
```

- ctyri pole: vyrobce, kod, kusy, V/NV,
- pole pro pridani fotky,
- seznam zdroju se 100% shodou.

Pravy prehled sbirky:

- kazdy model na jednom radku,
- sloupce:
  - poradi / body,
  - cislo vozu,
  - model,
  - jezdec,
  - VC/detail,
  - vyrobce,
  - kod,
  - PC,
  - V/NV.

Pri kliknuti na radek:

- vlevo se zobrazi detail modelu,
- pravy prehled se nesmi posunout na zacatek,
- vybrany radek je zvyrazneny/oramovany,
- pokud radek nema fotku, zustane vybrany a nic se neposouva.

Razeni:

- funguje jen pri vyberu konkretniho roku,
- nefunguje v kompletnim prehledu vsech let,
- defaultni poradi je puvodni poradi radku,
- razene sloupce:
  - poradi,
  - cislo vozu,
  - model,
  - jezdec,
  - PC,
  - V/NV.

Hledani:

- pole `Hledat` musi prijimat souvisle psani, ne jen jedno pismeno,
- proto bylo pridano zpozdene prekresleni a zachovani focusu/kurzoru.

## Provozni zkusenost: lokalni server

Puvodni spusteni pres:

```powershell
python -m http.server 4173
```

funguje v konzoli, ale pri skrytem behu pres `pythonw` muze vracet prazdnou odpoved, protoze `http.server` loguje do neexistujici konzole.

Oprava:

- pridany `app/serve_app.py`,
- pouziva `ThreadingHTTPServer`,
- vypina `log_message`,
- bezi stabilne na `127.0.0.1:4173`.

Spusteni v lokalnim vyvojovem prostredi:

```powershell
python app/serve_app.py
```

URL:

```text
http://127.0.0.1:4173/#/collection
```

## Cache verze aplikace

Po zmene dat nebo JS/CSS je nutne zvednout cache verzi v:

- `app/index.html`
- `app/src/app.js`

Priklad aktualni verze:

```text
20260809-1979-spark-photos-v3
```

Bez zvednuti verze muze prohlizec drzet stare `app-data.json` nebo stare JS.

## Kontrola kvality po kazdem importu roku

Po kazdem rocniku musi vzniknout audit:

- kolik modelu bylo nalezeno celkem,
- kolik modelu podle vyrobce,
- kolik modelu ma fotku,
- kolik fotek je funkcne overeno,
- kolik URL vraci 403/404,
- kolik modelu je bez katalogoveho kodu,
- kolik modelu je v kandidatech,
- kolik modelu bylo sparovano se sbirkou presne,
- kolik pravdepodobne,
- kolik zustalo nenalezeno,
- seznam podezrelych duplicit,
- seznam podezrelych kodu,
- seznam radku sbirky, ktere maji model vlastneny, ale katalog ho nenasel.

Audit nesmi byt jen pocet radku. Musi jasne ukazat, proc se model dostal do katalogu nebo do kandidatu.

## Zdroje pro master katalog

Prioritni zdroje:

- oficialni Spark katalog/API,
- oficialni Minichamps web,
- 143diecastmodels,
- F1 Scale Models stocklist,
- GrandPrixModels,
- DiecastLegends,
- Raceland,
- Carmodel,
- CK Modelcars,
- Miniatures-Minichamps,
- R.M.Toys,
- GP Cars Model,
- Tameo Kits,
- Vendilo Segrate,
- Artcraft Model,
- JVL Classics,
- eBay,
- dalsi specializovani prodejci a fora.

Kazdy zdroj musi byt ulozen do modelu jako URL. Pokud se model objevil ve vice zdrojich se 100% shodou, v detailu se maji vypsat vsechny.

## Cloudova architektura - cilovy stav

Soucasny stav je staticka lokalni aplikace. Cilovy cloudovy stav:

Frontend:

- webova aplikace,
- tabulkove pohledy,
- detail modelu s fotkami,
- filtry, razeni, kandidati,
- upload/pridani fotky.

Backend:

- API pro modely,
- API pro sbirku,
- API pro zdroje,
- API pro fotky,
- importni joby podle roku,
- auditni joby.

Databaze:

- `models`
- `manufacturers`
- `model_sources`
- `model_photos`
- `collection_items`
- `collection_matches`
- `candidate_matches`
- `import_runs`
- `audit_findings`

Fotky:

- hlavni fotka ulozena v databazi nebo object storage,
- thumbnaily ulozene lokalne/cloudove,
- originalni velikost se muze stahovat ze zdrojoveho URL az pri otevreni, pokud je zdroj stabilni,
- pro blokovane zdroje je nutne mit vlastni ulozeni kopie nahledu.

Importy:

- rocni import jako job,
- job uklada log,
- job lze opakovat,
- job nikdy nemaze rucne potvrzena data bez revize.

## Minimalni GitHub priprava

Pred vlozenim na GitHub:

- doplnit hlavni `README.md`,
- pridat tento projektovy dokument,
- pridat `.gitignore`,
- rozhodnout, zda commitovat velky `app-data.json`,
- rozhodnout, zda commitovat cache HTML stranek,
- oddelit surova data, vystupy a aplikaci,
- nedavat do repozitare osobni nebo citliva data, pokud ma byt verejny,
- popsat zdroje a limity pouziti obrazku,
- pripravit jednoduchy spousteci prikaz.

Doporucena public struktura:

```text
app/
  index.html
  src/
  assets/
  data/
  scripts/
docs/
  F1_143_MODEL_CATALOG_PROJECT.md
catalog_rules.py
match_model_catalog.py
README.md
```

Slozky `outputs/` a `input/` jsou lokalni/private a nemaji byt soucasti public repozitare.

## Otevrene ukoly

- Sjednotit rocni import do `app/scripts/build_year.py`.
- Doplnit oficialni Minichamps importer.
- Automatizovat fallback fotek pro Spark pri 403.
- Automatizovat overovani fotek po importu.
- Zavest per-year audit JSON/CSV.
- Doplnit cloudovy backend a databazovy model.
- Rozhodnout, ktere obrazky ukladat lokalne a ktere jen odkazovat.
- Vytvorit export/import osobni sbirky oddeleny od master katalogu.
- Zlepsit kandidaty tak, aby bylo jasne, proc vznikly.
- Doplnit dokumentaci nasazeni na cloud.

## Pravidlo pro dalsi praci

Pri kazdem dalsim rocniku:

1. Nejdriv nezavisly master katalog.
2. Potom fotky a overeni URL.
3. Potom deduplikace a validace kodu.
4. Az nakonec porovnani s osobni sbirkou.
5. Vysledek zapsat do tohoto dokumentu.
