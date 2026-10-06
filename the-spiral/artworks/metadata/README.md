# Spiral artworks - sources and licenses

The 40 images in `artworks/images/` are the collection shown in Curiosity Loop.
Every image and record came from an official museum open-access API through
`scripts/download_artworks.py`; nothing was typed in by hand. Fields a museum does not
provide are `null` in `artworks.json` (for example, the Met API has no provenance or description).

## Sources and licenses

- **The Metropolitan Museum of Art**: Open Access API (https://metmuseum.github.io/). Only
  objects with `isPublicDomain: true` were used. The Met releases these images under
  Creative Commons Zero (CC0): free to use, share and adapt for any purpose, no permission needed.
- **Cleveland Museum of Art**: Open Access API (https://openaccess-api.clevelandart.org/).
  Only objects with `share_license_status: CC0` were used, also free for any use.

No attribution is legally required under CC0, but this project credits each museum and keeps
the object number, credit line and official object URL for every work.

## How it was generated

1. `python3 scripts/download_artworks.py candidates` searched both APIs for spiral, vortex,
   coil, whorl, swirl, volute, rosette, shell and related terms, keeping only public-domain/CC0 works.
2. 40 works were chosen for visual variety and listed in order in `artworks/selection.json`.
3. `python3 scripts/download_artworks.py build` re-fetched each record, downloaded the museum
   image, resized it to 1600px on the long side (aspect ratio kept, never cropped) and wrote
   `artworks.json`, `artworks.csv` and this file.

## The works

### The Metropolitan Museum of Art (21)

- `001.jpg` **Spiral**. Etruscan, 7th–6th century BCE. 95.15.316. [object page](https://www.metmuseum.org/art/collection/search/246063). Public Domain (The Met Open Access, CC0)
- `004.jpg` **The Dioscuri on Monte Cavallo (recto); Study of a Spiral Staircase (verso)**. Maarten van Heemskerck, ca. 1533. 2003.158. [object page](https://www.metmuseum.org/art/collection/search/359491). Public Domain (The Met Open Access, CC0)
- `006.jpg` **Nebuleuse de la Lyre**. Paul Henry, ca. 1885. 1993.219. [object page](https://www.metmuseum.org/art/collection/search/266895). Public Domain (The Met Open Access, CC0)
- `008.jpg` **Nautilus cup**. Unknown maker, 1602. 17.190.604. [object page](https://www.metmuseum.org/art/collection/search/193582). Public Domain (The Met Open Access, CC0)
- `009.jpg` **Title page, from "Trofeo o sia Magnifica Colonna Coclide..." (The Trophy or Magnificent Spiral Column)**. Giovanni Battista Piranesi, 1774–79. 41.71.1.14(1). [object page](https://www.metmuseum.org/art/collection/search/406355). Public Domain (The Met Open Access, CC0)
- `010.jpg` **Spiral Ornament**. Colombian, before 16th century. X.105.34. [object page](https://www.metmuseum.org/art/collection/search/318219). Public Domain (The Met Open Access, CC0)
- `011.jpg` **Wooden Staircase at Chartres**. Henri-Jean-Louis Le Secq, 1852. 2005.100.35. [object page](https://www.metmuseum.org/art/collection/search/283108). Public Domain (The Met Open Access, CC0)
- `012.jpg` **Rough Waves**. Ogata Kōrin, ca. 1704–9. 26.117. [object page](https://www.metmuseum.org/art/collection/search/44918). Public Domain (The Met Open Access, CC0)
- `014.jpg` **Designs for Components of Stage Sets: at Bottom: Spiral and Wreathed-Colonnaded Pavillion with Central Arch Surmounted by Military Trophy and Another Hanging Inside Arch; at Top: Centralized Pavillion Decorated by Pediment Surmounted by Fountain**. Giuseppe Galli Bibiena, 1696–1756. 1972.713.63. [object page](https://www.metmuseum.org/art/collection/search/344497). Public Domain (The Met Open Access, CC0)
- `017.jpg` **Terracotta fragment of a cup with spiral and bands**. Minoan, ca. 1800–1700 BCE. 11.186.39. [object page](https://www.metmuseum.org/art/collection/search/248540). Public Domain (The Met Open Access, CC0)
- `019.jpg` **Intérieur à L'Escalier en Limaçon (Interior with a Spiral Staircase)**. Rodolphe Bresdin, 19th century. 51.504.33. [object page](https://www.metmuseum.org/art/collection/search/429812). Public Domain (The Met Open Access, CC0)
- `021.jpg` **Terracotta jar with nautiluses**. Helladic, Mycenaean, ca. 1400–1300 BCE. 14.147.2. [object page](https://www.metmuseum.org/art/collection/search/248912). Public Domain (The Met Open Access, CC0)
- `023.jpg` **Spiral Column Shaft**. Italo-Byzantine, first half 13th century. 49.60.10. [object page](https://www.metmuseum.org/art/collection/search/468306). Public Domain (The Met Open Access, CC0)
- `024.jpg` **Micrographic Design in the Shape of a Labyrinth**. Anonymous, early 17th century. 2014.96(12). [object page](https://www.metmuseum.org/art/collection/search/735626). Public Domain (The Met Open Access, CC0)
- `026.jpg` **Rock and Waves**. Maruyama Ōkyo 円山応挙, dated 1773. 57.156.1. [object page](https://www.metmuseum.org/art/collection/search/45422). Public Domain (The Met Open Access, CC0)
- `028.jpg` **Winds & Waves**. John Dillwyn Llewelyn, 1853–56. 2005.100.382 (6). [object page](https://www.metmuseum.org/art/collection/search/287896). Public Domain (The Met Open Access, CC0)
- `029.jpg` **Spirals**. Cypriot, n.d.. 74.51.3099. [object page](https://www.metmuseum.org/art/collection/search/242532). Public Domain (The Met Open Access, CC0)
- `031.jpg` **Column of Trajan**. Anonymous, 1544. 17.50.19-117. [object page](https://www.metmuseum.org/art/collection/search/403472). Public Domain (The Met Open Access, CC0)
- `035.jpg` **Acanthus Scroll with Rosette**. Anonymous, Italian, 17th century, 17th century. 52.570.93. [object page](https://www.metmuseum.org/art/collection/search/389386). Public Domain (The Met Open Access, CC0)
- `036.jpg` **Lunar Photograph, South Pole**. Paul Henry, 1890. 1995.125. [object page](https://www.metmuseum.org/art/collection/search/267137). Public Domain (The Met Open Access, CC0)
- `040.jpg` **Kasuga Deer Mandala (Kasuga shika mandara zu)**. Japan, late 14th century. 2015.300.11. [object page](https://www.metmuseum.org/art/collection/search/53187). Public Domain (The Met Open Access, CC0)

### Cleveland Museum of Art (19)

- `002.jpg` **Spiral Armilla**. Central Europe, Bronze Age, c. 1500 BCE. 1988.4. [object page](https://clevelandart.org/art/1988.4). CC0 (Cleveland Museum of Art Open Access)
- `003.jpg` **The Whirlpools of Awa**. Utagawa Hiroshige (Japanese, 1797–1858), 1857. 1930.183. [object page](https://clevelandart.org/art/1930.183). CC0 (Cleveland Museum of Art Open Access)
- `005.jpg` **Jar with Spiral Designs**. Northwest China, Neolithic period, Majiayao culture, Majiayao phase (3300–2650 BCE), 3300–2650 BCE. 2004.64. [object page](https://clevelandart.org/art/2004.64). CC0 (Cleveland Museum of Art Open Access)
- `007.jpg` **Illustration (Typhoon)**. Edward Alexander Wadsworth (British, 1889–1949), 1914–1915. 1987.50. [object page](https://clevelandart.org/art/1987.50). CC0 (Cleveland Museum of Art Open Access)
- `013.jpg` **Coil or Serpentine Fibula**. Etruscan, 900–700 BCE. 1970.90. [object page](https://clevelandart.org/art/1970.90). CC0 (Cleveland Museum of Art Open Access)
- `015.jpg` **Mirror with a Coiling Dragon**. China, Tang dynasty (618-907), 700s. 1995.367. [object page](https://clevelandart.org/art/1995.367). CC0 (Cleveland Museum of Art Open Access)
- `016.jpg` **The Great Whirlpool, Niagara**. America or Canada, 19th century, c. 1880s. 1992.336. [object page](https://clevelandart.org/art/1992.336). CC0 (Cleveland Museum of Art Open Access)
- `018.jpg` **In the Waves (Dans les Vagues)**. Paul Gauguin (French, 1848–1903), 1889. 1978.63. [object page](https://clevelandart.org/art/1978.63). CC0 (Cleveland Museum of Art Open Access)
- `020.jpg` **Ceremonial Disk with Grain Pattern (Bi)**. China, Warring States period (475–221 BCE), 475–221 BCE. 1952.567. [object page](https://clevelandart.org/art/1952.567). CC0 (Cleveland Museum of Art Open Access)
- `022.jpg` **Flüelen, from the Lake of Lucerne**. Joseph Mallord William Turner (British, 1775–1851), 1845. 1954.129. [object page](https://clevelandart.org/art/1954.129). CC0 (Cleveland Museum of Art Open Access)
- `025.jpg` **Addedomaros Stater: Horse, Branch, and Spiral Sun (reverse)**. England, Catuvellauni, 50 BCE–10 CE. 1969.147.b. [object page](https://clevelandart.org/art/1969.147.b). CC0 (Cleveland Museum of Art Open Access)
- `027.jpg` **Mirror with Concentric Circles and Linked Arcs**. China, Western Han dynasty (206 BCE–8 CE), late 200s–9 BCE. 1995.290. [object page](https://clevelandart.org/art/1995.290). CC0 (Cleveland Museum of Art Open Access)
- `030.jpg` **Snails**. Nagasawa Rosetsu (Japanese, 1754–1799), c. 1788–89. 1998.5. [object page](https://clevelandart.org/art/1998.5). CC0 (Cleveland Museum of Art Open Access)
- `032.jpg` **Mandala Base**. China, Ming dynasty (1368–1644), early 1400s. 1987.58. [object page](https://clevelandart.org/art/1987.58). CC0 (Cleveland Museum of Art Open Access)
- `033.jpg` **Spiral Ring with Isis and Serapis**. Greece or Italy, Rome (?), 1–100 CE. 1916.103. [object page](https://clevelandart.org/art/1916.103). CC0 (Cleveland Museum of Art Open Access)
- `034.jpg` **Waves**. Nakamura Hōchū (Japanese, d. 1819), late 1700s-early 1800s. 1999.90. [object page](https://clevelandart.org/art/1999.90). CC0 (Cleveland Museum of Art Open Access)
- `037.jpg` **Nautilus Reading Lamp**. Tiffany Glass & Decorating Company (America, New York, 1892–1902), c. 1899–1902. 1997.298. [object page](https://clevelandart.org/art/1997.298). CC0 (Cleveland Museum of Art Open Access)
- `038.jpg` **Clouds and Waves at the Wu Gorge**. Xie Shichen (Chinese, 1487–after 1567), c. 1547–67. 1968.213. [object page](https://clevelandart.org/art/1968.213). CC0 (Cleveland Museum of Art Open Access)
- `039.jpg` **Wave**. Aristide Maillol (French, 1861–1944), 1895–98. 1997.5. [object page](https://clevelandart.org/art/1997.5). CC0 (Cleveland Museum of Art Open Access)
