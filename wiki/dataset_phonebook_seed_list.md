# PTorrent Dataset Phonebook — Seed List

Working catalogue of every known public-facing dataset, by domain.
For each entry: name, what it is, API (Y/N), bulk dump (Y/N), notes on access.
This list is the manual seed for the automated phonebook. Convert each entry
to a `.ptorrent` of type `phonebook`. Verification status: UNVERIFIED unless marked.

robots.txt status, rate limits, and dump URLs belong in the generated .ptorrent file.
This document is the human-readable source of truth before automation.

---

## Computer Vision — General Image Classification

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| ImageNet (ILSVRC) | 14M+ images, 21,841 synsets. The CNN benchmark that started modern deep learning. | N | Y | image-net.org. Registration required. ~150GB for ILSVRC subset. |
| Open Images v7 | 9M images, 600 object classes, bounding boxes, relationships (Google). | Y | Y | storage.googleapis.com. Fully open. ~560GB. |
| COCO 2017 | 330K images, 80 object categories, segmentation, keypoints, captions. | N | Y | cocodataset.org. ~20GB. |
| Pascal VOC 2012 | 11,530 images, 20 classes, detection + segmentation. Classic benchmark. | N | Y | host.robots.ox.ac.uk. ~2GB. |
| CIFAR-10 / CIFAR-100 | 60K 32×32 images (10 or 100 classes). Canonical small-image benchmark. | N | Y | cs.toronto.edu. ~170MB. |
| STL-10 | 13K 96×96 images, semi-supervised split. | N | Y | cs.stanford.edu. |
| MNIST | 70K 28×28 handwritten digits. The "Hello World" of vision. | N | Y | yann.lecun.com. |
| Fashion-MNIST | MNIST-format, 10 clothing categories (Zalando). | N | Y | GitHub/zalandoresearch. |
| EMNIST | Extended MNIST — handwritten letters + digits. | N | Y | nist.gov. |
| Kuzushiji-MNIST | Classic Japanese cursive character recognition. | N | Y | GitHub/rois-codh. |
| Caltech-101 / 256 | 101/256 object categories. Pre-ImageNet benchmark. | N | Y | vision.caltech.edu. |
| SUN Database | 899 scene categories, 130K+ images (MIT). | N | Y | vision.princeton.edu. |
| Places365 | 365 scene categories, 1.8M images (MIT/CSAIL). | N | Y | places2.csail.mit.edu. |
| ADE20K | 150-class semantic segmentation, 25K images. | N | Y | groups.csail.mit.edu/vision/datasets. |
| Visual Genome | 108K images, 3.8M object instances, region descriptions, QA. | Y | Y | visualgenome.org. |
| Flickr30k | 31K images, 5 captions each. Image-text alignment. | N | Y | shannon.cs.illinois.edu. |
| LSUN | Large-scale scene understanding (bedroom, church, etc.). | N | Y | GitHub/fyu/lsun. 1TB+. |
| Oxford Buildings / Paris Buildings | Image retrieval benchmarks, landmark photos. | N | Y | robots.ox.ac.uk. |
| Google Landmarks v2 | 5M images, 200K landmarks (GLDv2). | N | Y | GitHub/cvdfoundation/google-landmarks. |
| iNaturalist 2021 | 2.7M images, 10K species (plants, animals, fungi). | Y | Y | inaturalist.org API. Competition subset on Kaggle. |
| iMaterialist | Fashion/furniture product attributes. | N | Y | Kaggle competition. |
| DeepFashion | 800K clothing images, landmarks, attributes, retrieval. | N | Y | liuziwei7.github.io/DeepFashion. |
| Food-101 | 101 food categories, 101K images. | N | Y | vision.ee.ethz.ch. |
| Stanford Cars | 196 car classes (make/model/year), 16K images. | N | Y | ai.stanford.edu/~jkrause/cars. |
| FGVC Aircraft | 102 aircraft variants, 10K images. | N | Y | robots.ox.ac.uk/~vgg/data/fgvc-aircraft. |
| Oxford-IIIT Pets | 37 pet breeds, 7,349 images + segmentation. | N | Y | robots.ox.ac.uk/~vgg/data/pets. |
| CelebA | 200K celebrity face images, 40 attribute annotations. | N | Y | mmlab.ie.cuhk.edu.hk. |
| FFHQ | 70K high-quality face images (Nvidia, StyleGAN training). | N | Y | GitHub/NVlabs/ffhq-dataset. |
| LFW | Labeled Faces in the Wild — face verification. 13K images. | N | Y | vis-www.cs.umass.edu/lfw. |
| VGGFace2 | 3.3M face images, 9K identities. | N | Y | robots.ox.ac.uk/~vgg/data/vgg_face2. |
| FER2013 | Facial expression recognition, 35K 48×48 images. | N | Y | Kaggle. |
| AffectNet | 450K facial images with valence/arousal annotations. | N | Y | mohammadmahoor.com/affectnet. |
| MPII Human Pose | 25K images, 40K people, 16 body joints. | N | Y | human-pose.mpi-inf.mpg.de. |
| WIDER FACE | 32K images, 393K face bounding boxes. | N | Y | shuoyang1213.me/WIDERFACE. |
| DOTA v2 | Aerial object detection, 1.8M instances, 18 classes. | N | Y | captain-whu.github.io/DOTA. |
| xView | Satellite imagery, 60 object classes, overhead view. | N | Y | xviewdataset.org. Registration required. |
| SpaceNet | Satellite building/road/PoI detection (AWS). | Y | Y | spacenet.ai. S3 bucket. |
| EuroSAT | Sentinel-2 land-use classification, 27K patches. | N | Y | GitHub/phelber/EuroSAT. |
| BigEarthNet | Sentinel-1/2 multi-label land cover, 590K patches. | N | Y | bigearth.net. |
| CLEVR | Synthetic compositional QA images (Facebook/Stanford). | N | Y | cs.stanford.edu/people/jcjohns/clevr. |
| GQA | 22M QA pairs on scene graphs, compositional reasoning. | N | Y | cs.stanford.edu/people/dorarad/gqa. |
| VQA v2 | 1.1M QA pairs on COCO images. | N | Y | visualqa.org. |

---

## Computer Vision — Medical Imaging

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| NIH Chest X-Ray14 | 112K chest X-rays, 14 disease labels. | N | Y | nihcc.app.box.com. ~42GB. |
| CheXpert | 224K chest X-rays (Stanford). Uncertain labels. | N | Y | stanfordmlgroup.github.io/competitions/chexpert. |
| MIMIC-CXR | 377K chest X-rays + radiology reports (MIT/Beth Israel). | N | Y | physionet.org. HIPAA training required. |
| PadChest | 160K chest X-rays, 174 findings (Spanish). | N | Y | bimcv.cipf.es/bimcv-projects/padchest. |
| VinDr-CXR | 18K Vietnamese chest X-rays. | N | Y | physionet.org. |
| BraTS | Multimodal brain tumor MRI, annual challenge. | N | Y | synapse.org. Registration. |
| OASIS | 1K+ brain MRI scans, longitudinal aging data. | N | Y | oasis-brains.org. |
| ADNI | Alzheimer's MRI/PET/genomics longitudinal dataset. | N | Y | adni.loni.usc.edu. Application required. |
| HCP | Human Connectome Project — high-res fMRI/diffusion MRI. | N | Y | humanconnectome.org. Registration. |
| OpenNeuro | Open neuroimaging repository (fMRI, EEG, MEG). | Y | Y | openneuro.org. S3-backed. |
| ISIC Archive | 33K+ dermoscopy images, skin lesion classification. | Y | Y | isic-archive.com. Full API. |
| HAM10000 | 10K dermoscopy images, 7 skin lesion classes. | N | Y | dataverse.harvard.edu. |
| CAMELYON16/17 | Breast cancer metastasis in histopathology slides. | N | Y | camelyon16.grand-challenge.org. |
| TCGA | The Cancer Genome Atlas — genomics + pathology slides. | Y | Y | portal.gdc.cancer.gov. Full GDC API. |
| LUNA16 | Lung nodule detection in CT scans, 888 scans. | N | Y | luna16.grand-challenge.org. |
| DRIVE/STARE | Retinal vessel segmentation, fundus images. | N | Y | drive.grand-challenge.org. |
| Diabetic Retinopathy (Kaggle) | 35K retinal images, 5-level DR grading. | N | Y | Kaggle competition (EyePACS). |
| MedMNIST v2 | 18 standardized medical image datasets in MNIST format. | N | Y | medmnist.com. |
| DeepLesion | 32K CT lesion annotations (NIH). | N | Y | nihcc.app.box.com. |
| BreakHis | Breast cancer histology, 7,909 microscopy images, magnification levels. | N | Y | web.inf.ufpr.br/vri/databases/breast-cancer-histopathological. |
| PathMNIST / TissueMNIST | Colon pathology and kidney tissue (from MedMNIST). | N | Y | medmnist.com. |

---

## Computer Vision — Autonomous Driving / Surveillance

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| KITTI | Stereo, optical flow, depth, 3D object detection, tracking. Karlsruhe. | N | Y | cvlibs.net/datasets/kitti. |
| Cityscapes | Urban street-scene segmentation, 50 cities. | N | Y | cityscapes-dataset.com. Registration. |
| nuScenes | 1000 driving scenes, 3D boxes, LiDAR, 6 cameras, radar. | N | Y | nuscenes.org. |
| Waymo Open Dataset | 2000 segments, high-res LiDAR + camera. | N | Y | waymo.com/open. Application. |
| BDD100K | 100K driving videos, 10 tasks (detection, lane, drivable area). | N | Y | bdd-data.berkeley.edu. |
| A2D2 | Audi autonomous driving: LiDAR + camera, semantic segmentation. | N | Y | audi-electronics-venture.de/aev/web/de/a2d2.html. |
| Comma.ai | 45 hours of highway driving (comma.ai). | N | Y | GitHub/commaai/comma2k19. |
| Udacity Self-Driving | Multiple labelled driving datasets. | N | Y | GitHub/udacity/self-driving-car. |
| CamVid | Cambridge-driving video, per-frame labelled. | N | Y | mi.eng.cam.ac.uk/research/projects/VideoRec/CamVid. |
| GTSRB | German Traffic Sign Recognition Benchmark, 50K images. | N | Y | benchmark.ini.rub.de. |
| LISA Traffic Sign | US traffic sign detection (UCSD). | N | Y | cvrr.ucsd.edu/LISA/lisa-traffic-sign-dataset. |
| UA-DETRAC | 10 hours CCTV traffic video, 140K annotated frames. | N | Y | detrac.smiles.buaa.edu.cn. |
| MOT Challenge | Multiple object tracking benchmarks (pedestrians, vehicles). | N | Y | motchallenge.net. |
| DanceTrack | Multi-person tracking in dance videos. | N | Y | GitHub/DanceTrack. |
| Market-1501 | Person re-identification, 32K images, 1,501 identities. | N | Y | zheng-lab.cecs.anu.edu.au. |
| CrowdHuman | Dense pedestrian detection, 15K images. | N | Y | crowdhuman.org. |

---

## Crowdsourced / Citizen Science / Game Datasets

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| EVE Online — Project Discovery | Multiple phases: exoplanet transit (TESS), COVID-19 protein (Human Protein Atlas), cancer cells (Allen Institute). Players classify scientific data in-game. Output shared with scientists. | N | Partial | Phase 1/2/3 results published in papers. Raw classifications via CCP/citizen science partners. |
| FoldIt | Protein structure prediction game. Player solutions contributed to papers including protein fold discoveries (Science, 2011). | N | Partial | fold.it. Some solutions publicly released. Game replay data partially available. |
| Rosetta@home | Distributed protein folding (BOINC). Contributed to AlphaFold validation. | N | Partial | boinc.bakerlab.org. |
| Galaxy Zoo | Galaxy morphology classification — 900K galaxies, millions of classifications. Flagship Zooniverse project. | N | Y | data.galaxyzoo.org. Full classification tables downloadable. |
| Galaxy Zoo 2 | Detailed morphology of 300K SDSS galaxies. | N | Y | data.galaxyzoo.org. |
| Moon Zoo | Crater and boulder mapping from LRO images. | N | Y | Zooniverse archive. |
| Planet Four | Mars recurring slope linea mapping from HiRISE images. | N | Y | Zooniverse archive. |
| Snapshot Serengeti | Wildlife camera trap classification — 1.2M images. | N | Y | snapshotserengeti.org. Lila.science. |
| Chimp&See | Chimpanzee behavior from camera traps (Pan African Programme). | N | Partial | Zooniverse. |
| Penguin Watch | Penguin colony monitoring from time-lapse cameras. | N | Y | Zooniverse. |
| Bat Detective | Bat echolocation call identification from audio spectrograms. | N | Y | Zooniverse. |
| Whale FM | Killer whale and pilot whale call classification. | N | Y | Zooniverse. |
| Old Weather | Historical weather logs transcribed from Royal Navy ship logs. | N | Y | Zooniverse. Contributed to ICOADS. |
| Notes from Nature | Museum specimen label transcription (insects, plants, fossils). | N | Y | Zooniverse. |
| Ancient Lives | Egyptian Oxyrhynchus Papyri transcription. | N | Y | Zooniverse. |
| Stardust@home | Interstellar dust particle identification in aerogel images. | N | Partial | stardustathome.ssl.berkeley.edu. |
| CAPTCHA annotation data | reCAPTCHA v1 used crowd to digitize books (scanned text). reCAPTCHA v2 used to label street signs/storefronts. Aggregate output contributed to Maps. | N | N | Not formally released — embedded in Google products. |
| iNaturalist | 140M+ species observations, photos, crowd ID. Global biodiversity mapping. | Y | Y | api.inaturalist.org. Full dump via GBIF. |
| eBird | 1B+ bird observation records, Cornell Lab of Ornithology. | Y | Y | ebird.org/data/download. |
| GBIF | Global Biodiversity Information Facility — aggregates 100+ databases, 2B+ occurrence records. | Y | Y | gbif.org/occurrence/download. Darwin Core. |
| iMet Collection (Kaggle) | Metropolitan Museum artwork attribute classification by crowd. | N | Y | Kaggle competition. |
| Rijksmuseum Challenge | Dutch Golden Age paintings — artist, material, creation date. | N | Y | rijksmuseum.nl/en/research/conduct-research/data. |
| WikiArt | 250K artwork images, style/genre/artist labels (Wikipedia-sourced). | N | Partial | wikiart.org. Partial dumps floating on Kaggle/HF. |
| OpenStreetMap | Crowd-mapped global geography. 10B+ nodes. | Y | Y | planet.openstreetmap.org. Daily diffs. Geofabrik regional dumps. |
| Wikipedia / Wikidata | Crowd-curated encyclopedia (Wikipedia) + structured knowledge (Wikidata, 60M+ items). | Y | Y | dumps.wikimedia.org. Monthly. |
| Wiktionary | Crowd-built multilingual dictionary. | Y | Y | dumps.wikimedia.org. |
| Duolingo SLAM | Second Language Acquisition Modeling — learner response data. | N | Y | sharedtask.duolingo.com. |
| Human Protein Atlas | Cell-level protein localization, crowd-assisted annotation. | Y | Y | proteinatlas.org/about/download. |

---

## Numismatics / Collectibles / Appraisal / Authentication

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| PCGS CoinFacts | Coin images with PCGS grades (MS-70 scale), mintage data, auction records. Most comprehensive US coin reference. | N | Partial | pcgs.com/coinfacts. Scraping requires robots.txt review. No official dump. Significant IP concerns — contact PCGS. |
| NGC Coin Census | Graded coin population reports (NGC). | N | N | ngccoin.com. Population data via web, no API or dump. |
| American Numismatic Society | 600K+ coin records, images, from ancient to modern. Scholarly. | Y | Y | numismatics.org/search. SPARQL endpoint. Linked Open Data. **Best academic source.** |
| British Museum Collection | Ancient and world coins, 800K+ objects online. High-res images. | Y | Y | collection.britishmuseum.org. SPARQL/API. CC-BY-NC-SA images. |
| Smithsonian National Numismatic Collection | ~1.6M objects. Digitized subset. | Y | N | americanhistory.si.edu/numismatics. No full dump. |
| Wildwinds | Ancient Greek, Roman, Byzantine coin type reference. Images + attributions. | N | Partial | wildwinds.com. No API. HTML scrape needed. |
| CRRO (Coin Register of Roman Republic Online) | Oxford/ANS — Republican Roman coins. | Y | Y | numismatics.org/crro. SPARQL. |
| OCRE (Online Coins of the Roman Empire) | 70K+ Imperial Roman coin types. | Y | Y | numismatics.org/ocre. SPARQL. Full RDF dump. |
| Coin Archives | Auction records for ancient and world coins. | N | N | coinarchives.com. Subscription. No public API or dump. |
| Acsearch | Numismatic auction database. | N | N | acsearch.info. Subscription. |
| Ha'Penny Press image archive | Historical British coinage images. | N | Partial | Partial open access. |
| Coins Detected (IEEE/research) | CNN benchmark datasets for coin classification in ML papers. | N | Y | Various — search IEEE Xplore for "coin recognition dataset". Several released on request or GitHub. |
| NUNUM | Numismatic dataset from University of Novi Sad. Balkan coin images. | N | Partial | Contact authors. Published in research papers. |
| Fitzwilliam Museum Coins | Cambridge — extensive ancient coin collection, partially digitized. | Y | Partial | data.fitzmuseum.cam.ac.uk. |
| Sylloge Nummorum Graecorum (SNG) | Greek coin typology — multiple national volumes digitized. | N | Partial | sng.ans.org. |
| eBay sold listings (Coins category) | Graded coin sale prices + images — best real-world pricing signal. | N | N | robots.txt restrictive. Historical data via eBay Terapeak (subscription). No official dump. |
| Heritage Auctions archives | US and world coin auction results, high-res images. | N | N | ha.com. No API. Historical results accessible via web. |
| Stack's Bowers auction archives | Major US rare coin auction records. | N | N | stacksbowers.com. No public dump. |
| Greysheet / CDN | Dealer bid/ask wholesale pricing. | N | N | greysheet.com. Subscription. |
| Paper Money Guarantee (PMG) | Banknote grading population + images. | N | N | pmgnotes.com. No dump. |
| PCGS Currency | Graded banknote census. | N | N | pcgscurrency.com. |
| World Banknote archive (Colnect) | 100K+ world banknote catalogue with images. | Y | Partial | colnect.com/en/banknotes. API exists. |
| Colnect Coins | 900K+ world coin catalogue — type images, mintages, years. | Y | Partial | colnect.com/en/coins. API exists. Best free world coin catalogue. |
| Numista | Community coin catalogue — 700K+ types, mintages, images. | Y | Partial | en.numista.com/api. Free API with registration. |

---

## Automotive / Vehicle Parts / Repair

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| AllData | Vehicle repair data — every component, torque spec, wiring diagram, recall, TSB for every US vehicle. Industry standard. | N | N | alldata.com. Subscription only. No public access. Most comprehensive source in existence. |
| Mitchell1 ProDemand | Competitor to AllData. Same scope. | N | N | mitchell1.com. Subscription. |
| Chilton / MOTORS | OEM repair manuals, competitor data. | N | N | chilton.cengage.com. Subscription. |
| NHTSA Vehicle Safety Complaints | Consumer complaint database — make/model/component/failure. | Y | Y | api.nhtsa.dot.gov. Full CSV dumps. **Public domain.** |
| NHTSA Recall Database | Every US vehicle recall since 1966. | Y | Y | api.nhtsa.dot.gov/recalls. |
| NHTSA Crash Test Data (NCAP) | 5-star safety ratings, crash test videos, sensor data. | Y | Y | nhtsa.gov/research-data/databases-and-software. |
| EPA Fuel Economy | MPG for every vehicle 1984–present. | Y | Y | fueleconomy.gov/feg/download.do. Full dump. |
| ACES (AutoCare) | Aftermarket Catalog Exchange Standard — parts fitment database. Industry standard for parts compatibility. | N | N | autocare.org. Licensing required. |
| PIES (Product Information Exchange Standard) | Parts product data standard. Companion to ACES. | N | N | autocare.org. Licensing. |
| VINquery / NHTSA VIN API | VIN decode: year/make/model/trim/engine from VIN. | Y | N | api.nhtsa.dot.gov/vehicles/DecodeVinValuesExtended. Free. |
| CARFAX / AutoCheck | Vehicle history reports — accidents, title, odometer. | N | N | Subscription. No public API or dump. |
| GoodCar | Vehicle history, similar to CARFAX. | Y | N | goodcar.com/api. Freemium. |
| OBD-II DTC Database | Diagnostic Trouble Code definitions — P/B/C/U codes. | N | Partial | Multiple open sources (OBD2-database.com, obdii.com). No authoritative single dump. |
| SAE J1979 / ISO 15031 | OBD-II protocol standards. Not datasets per se, but define the data space. | N | N | sae.org. Subscription. |
| Stanford Cars Dataset | 16,185 images, 196 classes (make/model/year). CNN benchmark. | N | Y | ai.stanford.edu/~jkrause/cars. |
| CompCars | 136K car images, 1,716 models (Chinese vehicles). | N | Y | mmlab.ie.cuhk.edu.hk/datasets/comp_cars. |
| VMMRdb | 291,752 images, 9,170 models, 712 makes. | N | Y | GitHub/faezetta/VMMRdb. |
| UA-DETRAC | Traffic surveillance — vehicle detection and tracking. | N | Y | detrac.smiles.buaa.edu.cn. |
| Comma2k19 | 33 hours highway driving, CAN bus data, GPS. | N | Y | GitHub/commaai/comma2k19. |
| Open Vehicle Monitoring System (OVMS) | OBD/CAN telemetry from real vehicles. Community contributed. | Y | Partial | ovms.io. |
| US DOT FARS | Fatality Analysis Reporting System — crash records 1975–present. | Y | Y | nhtsa.gov/research-data/fatality-analysis-reporting-system-fars. |
| GES / CRSS | General Estimates System — police-reported crashes. | N | Y | nhtsa.gov/crash-data-systems/crash-report-sampling-system. |
| TomTom Traffic Statistics | Congestion, speed data by city. | Y | Partial | developer.tomtom.com. API freemium. No full dump. |
| HERE Traffic | Road speed / flow data. | Y | N | developer.here.com. Freemium. |
| OpenStreetMap road network | Full world road graph. | Y | Y | geofabrik.de. |
| StreetLevel imagery (Mapillary) | 1.5B street-level images with traffic sign / object annotations. | Y | Y | mapillary.com/developer. Full API. CC-BY-SA 4.0 data. |
| GTFS / GTFS-RT | General Transit Feed Specification — transit schedules and real-time data, every city. | Y | Y | transit.land. MobilityDatabase. Hundreds of feeds. |

---

## NLP / Text Corpora

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| Common Crawl | Petabyte-scale web crawl, monthly snapshots since 2008. | N | Y | commoncrawl.org. S3 public access. ~400TB/crawl. |
| The Pile | 825GB diverse English text (EleutherAI). 22 subsets. | N | Y | pile.eleuther.ai. HuggingFace mirror. |
| RedPajama v2 | 30T token multilingual text (Together AI). | N | Y | HuggingFace. |
| C4 | Colossal Clean Crawled Corpus (Google T5 training). | N | Y | HuggingFace/datasets. |
| ROOTS | 1.6TB multilingual (BLOOM training, BigScience). | N | Y | HuggingFace. |
| OSCAR | Open Super-large Crawled Aggregated coRpus. 166 languages. | N | Y | oscar-project.eu. HuggingFace. |
| Wikipedia dumps | All language editions. Monthly. | N | Y | dumps.wikimedia.org. |
| Project Gutenberg | 70K public-domain books. | Y | Y | gutenberg.org. rsync mirror available. |
| Books3 / BookCorpus successors | Sourced book text for pretraining. Legally contentious. | N | Partial | Hosting varies. The Pile includes Books3. |
| OpenWebText | Open replica of WebText (GPT-2 training data). | N | Y | HuggingFace/datasets. |
| CC-News | CommonCrawl news subset, 2017–present. | N | Y | commoncrawl.org. |
| OPUS | Open Parallel Corpus — 100+ language pairs, 90 datasets. | Y | Y | opus.nlpl.eu. Full API + dumps. |
| CCAligned | Web-aligned multilingual pairs, 100 languages. | N | Y | HuggingFace. |
| FLORES-200 | Evaluation for 200 languages (Meta). | N | Y | GitHub/facebookresearch/flores. |
| SQuAD 1.1 / 2.0 | Stanford QA — 100K/150K questions on Wikipedia. | N | Y | rajpurkar.github.io/SQuAD-explorer. |
| Natural Questions | 320K Google search questions + Wikipedia passages. | N | Y | ai.google.com/research/NaturalQuestions. |
| TriviaQA | 650K trivia QA pairs. | N | Y | nlp.cs.washington.edu/triviaqa. |
| MS MARCO | 1M queries, 8.8M passages (Microsoft). | N | Y | microsoft.github.io/msmarco. |
| HotpotQA | Multi-hop reasoning QA, 113K questions. | N | Y | hotpotqa.github.io. |
| MultiNLI | 433K sentence pairs, 10 genres, inference labels. | N | Y | nyu.edu/projects/bowman/multinli. |
| SNLI | Stanford NLI — 570K premise/hypothesis pairs. | N | Y | nlp.stanford.edu/projects/snli. |
| SST-2 / SST-5 | Stanford Sentiment Treebank (movie reviews). | N | Y | nlp.stanford.edu/sentiment. |
| IMDb reviews | 50K movie reviews, binary sentiment. | N | Y | ai.stanford.edu/~amaas/data/sentiment. |
| Amazon Reviews | 233M product reviews across 43 categories (McAuley). | N | Y | nijianmo.github.io/amazondataset. |
| AG News | 127K news article classification. | N | Y | HuggingFace/datasets. |
| Universal Dependencies | Treebanks for 140+ languages. | Y | Y | universaldependencies.org. GitHub. |
| Penn Treebank | 1M word Wall Street Journal parse trees. | N | N | LDC. Subscription. |
| OntoNotes 5.0 | Coreference, NER, parse trees (LDC). | N | N | LDC. Subscription. |
| CoNLL 2003 NER | English/German named entity recognition. | N | Y | HuggingFace/datasets. |
| StackExchange dumps | All 170+ SE sites — posts, answers, comments, votes. | N | Y | archive.org/details/stackexchange. Quarterly. |
| Reddit PushShift | Historical Reddit posts/comments. Partially frozen 2023+. | N | Partial | academictorrents.com has historical snapshots. |
| GitHub Code (The Stack) | 3TB+ deduplicated code across 350+ languages (BigCode). | N | Y | HuggingFace/bigcode/the-stack. |
| CodeParrot | Cleaned GitHub Python code. | N | Y | HuggingFace. |
| USPTO Patents | Full-text patent documents, 1976–present. | Y | Y | patentsview.org/download. Bulk downloads. |
| SEC EDGAR Full-Text | All 10-K, 10-Q, 8-K filings. | Y | Y | efts.sec.gov/LATEST/search-index. Bulk downloads. |
| Enron Email Corpus | 500K+ emails (Enron employees). | N | Y | cs.cmu.edu/~./enron. |
| PubMed Central OA | 4M+ full-text biomedical papers. | Y | Y | ncbi.nlm.nih.gov/pmc/tools/ftp. FTP bulk download. |
| arXiv bulk access | 2M+ scientific preprints, LaTeX source. | N | Y | arxiv.org/help/bulk_data. S3 bucket. |

---

## Audio / Speech / Music

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| LibriSpeech | 1000 hours audiobook speech, 2,484 speakers. | N | Y | openslr.org/12. |
| Common Voice 17 | 30,000+ hours, 100+ languages (Mozilla). | N | Y | commonvoice.mozilla.org/datasets. |
| VoxCeleb 1/2 | 7K+ celebrity speaker recognition. | N | Y | robots.ox.ac.uk/~vgg/data/voxceleb. |
| VCTK | 109 English speakers, 400 sentences each. | N | Y | datashare.ed.ac.uk. |
| LJSpeech | Single speaker TTS, 13,100 short clips. | N | Y | keithito.com/LJ-Speech-Dataset. |
| TIMIT | 630 speakers, 8 US dialects, phoneme-aligned. | N | N | LDC subscription. |
| TED-LIUM 3 | 452 hours TED talks, 3K speakers. | N | Y | openslr.org/51. |
| AISHELL-1 | 178 hours Mandarin speech, 400 speakers. | N | Y | openslr.org/33. |
| AudioSet | 2M 10-second YouTube clips, 632 audio event classes (Google). | N | Y | research.google.com/audioset. Labels + YouTube IDs. |
| ESC-50 | 2000 environmental sound clips, 50 classes. | N | Y | GitHub/karolpiczak/ESC-50. |
| UrbanSound8K | 8732 urban sound clips, 10 classes. | N | Y | urbansounddataset.weebly.com. |
| FreeSound | 500K+ community-uploaded sound effects. | Y | Partial | freesound.org/apiv2. Requires registration. |
| NSynth | 300K musical notes, 1000 instruments (Magenta/Google). | N | Y | magenta.tensorflow.org/datasets/nsynth. |
| GTZAN | 1000 music clips, 10 genres, 30 seconds. Classic music classification. | N | Y | marsyas.info/downloads/datasets. |
| MagnaTagATune | 25K audio clips, 188 tags. | N | Y | mirg.city.ac.uk/datasets/magnatagatune. |
| MusicNet | 330 classical music recordings, note annotations. | N | Y | zenodo.org/record/5120004. |
| MAESTRO | 200+ hours piano MIDI + audio, aligned (Magenta). | N | Y | magenta.tensorflow.org/datasets/maestro. |
| Slakh2100 | 2100 multi-track stems (synthesized from MIDI). | N | Y | www.slakh.com. |
| VGGSound | 200K video clips, 309 audio classes (VGG). | N | Y | robots.ox.ac.uk/~vgg/data/vggsound. |
| DCASE Challenges | Acoustic scene classification, sound event detection — annual challenges. | N | Y | dcase.community/challenge. |
| AMI Meeting Corpus | 100 hours meeting recordings + transcripts. | N | Y | groups.inf.ed.ac.uk/ami/corpus. |
| CHiME Challenges | Noisy speech recognition in domestic environments. | N | Y | chimechallenge.org. |
| MUSDB18 | 150 professionally mixed songs with stems. | N | Y | zenodo.org/record/3338373. |

---

## Astronomy / Astrophysics / Cosmology

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| SDSS DR18 | Sloan Digital Sky Survey — 500M objects, spectra, photometry. | Y | Y | skyserver.sdss.org. CasJobs SQL + bulk downloads. |
| Gaia DR3 | 1.8B stellar objects, proper motions, parallaxes (ESA). | Y | Y | gea.esac.esa.int/tap-server/tap. TAP/ADQL. |
| 2MASS | All-sky near-infrared survey, 500M sources. | Y | Y | irsa.ipac.caltech.edu. IRSA API. |
| WISE / CatWISE2020 | All-sky mid-infrared, 1.8B sources. | Y | Y | irsa.ipac.caltech.edu. |
| PanSTARRS DR2 | 3π sky survey, 1.6B unique objects. | Y | Y | catalogs.mast.stsci.edu. MAST. |
| DES DR2 | Dark Energy Survey, 700M objects, weak lensing. | Y | Y | des.ncsa.illinois.edu/easyweb. |
| HST Archive (MAST) | Hubble Space Telescope data, 1990–present. | Y | Y | mast.stsci.edu. Petabytes. |
| JWST Archive | James Webb Space Telescope, 2022–present. | Y | Y | mast.stsci.edu/portal/Mashup/Clients/Mast/Portal.html. |
| NASA Exoplanet Archive | 5,600+ confirmed exoplanets, light curves, spectra. | Y | Y | exoplanetarchive.ipac.caltech.edu. Full API. |
| LIGO Open Science Center | Gravitational wave strain data, O1/O2/O3. | Y | Y | gw-openscience.org. |
| Chandra X-ray Archive | X-ray observatory data 1999–present. | Y | Y | cda.harvard.edu. |
| XMM-Newton Archive | ESA X-ray multi-mirror mission. | Y | Y | nxsa.esac.esa.int. |
| Fermi LAT | Gamma-ray all-sky data, 2008–present. | Y | Y | fermi.gsfc.nasa.gov/ssc/data. |
| Planck Legacy Archive | CMB temperature/polarization maps. | Y | Y | pla.esac.esa.int. |
| ACT Data Release | Atacama Cosmology Telescope CMB maps. | N | Y | act.princeton.edu. |
| ALMA Archive | Millimeter/submillimeter interferometry. | Y | Y | almascience.org/aq. |
| VLA Archive | Very Large Array radio data 1976–present. | Y | Y | archive.nrao.edu. |
| LMFDB | L-functions, modular forms, elliptic curves, Riemann zeros. | Y | Y | lmfdb.org/api. JSON API. |
| NED | NASA/IPAC Extragalactic Database — 1B+ objects. | Y | Y | ned.ipac.caltech.edu. |
| SIMBAD | 14M astronomical objects (CDS Strasbourg). | Y | Y | simbad.u-strasbg.fr. TAP + scripted queries. |
| VizieR | 22,000+ astronomical catalogues (CDS). | Y | Y | vizier.cds.unistra.fr. TAP. |
| SPARC | 175 galaxy rotation curves, baryonic mass models. | N | Y | astroweb.cwru.edu/SPARC. |
| NASA ADS | Bibliographic records + full-text for astronomy papers. | Y | Y | ui.adsabs.harvard.edu/help/api. |
| SDSS SkyServer | Web-accessible SQL queries into SDSS catalog. | Y | Y | skyserver.sdss.org/dr18/SkyServerWS/SearchTools. |
| Galaxy Zoo Classifications | Morphology labels for 900K SDSS galaxies. | N | Y | data.galaxyzoo.org. |
| OpenAstronomy / astropy | Software ecosystem; some datasets distributed via astropy.io.fits. | Y | Y | |
| LAMOST | Chinese sky survey — 10M+ spectra. | Y | Y | dr9.lamost.org. |

---

## Geospatial / Climate / Environment

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| NASA Earthdata | MODIS, LANDSAT, SRTM, GPM, AIRS, GRACE and hundreds more. | Y | Y | earthdata.nasa.gov. OPeNDAP, Earthdata API. |
| ESA Copernicus (Sentinel) | Sentinel-1 SAR, Sentinel-2 optical, Sentinel-5P atmosphere. | Y | Y | scihub.copernicus.eu. Copernicus Data Space. |
| USGS Earth Explorer | LandSat 1–9, ASTER, SRTM, aerial imagery. | Y | Y | earthexplorer.usgs.gov. |
| NOAA CDO | Climate Data Online — surface weather, marine, storm data. | Y | Y | ncei.noaa.gov/cdo-web/api. |
| ERA5 | ECMWF global atmospheric reanalysis, 1940–present, 31km. | Y | Y | cds.climate.copernicus.eu. |
| SRTM / CopDEM | Global 30m/90m digital elevation models. | N | Y | NASA/ESA public FTP. |
| WorldClim v2 | Global climate variables (temp, precip) 1970–2000, 1km. | N | Y | worldclim.org/data/worldclim21.html. |
| CHELSA | Climate at High Resolution for Earth's Land Surface Areas. | N | Y | chelsa-climate.org. |
| GHCN-Daily | Global Historical Climatology Network — 100K+ stations. | Y | Y | ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily. |
| CO₂ Mauna Loa | Keeling Curve — atmospheric CO₂ 1958–present. | N | Y | scrippsco2.ucsd.edu. |
| PANGAEA | Earth and environmental science data repository — 440K+ datasets. | Y | Y | pangaea.de. OAI-PMH, REST API. |
| Global Forest Watch | Forest cover change, fires, deforestation alerts. | Y | Y | globalforestwatch.org/help/map/guides. GEE integration. |
| Hansen Forest Cover | Global tree cover loss/gain 2000–present (UMD). | N | Y | earthenginepartners.appspot.com/science-2013-global-forest. |
| OBIS | Ocean Biodiversity Information System — 100M+ marine occurrence records. | Y | Y | api.obis.org. Darwin Core. |
| GBIF | Global biodiversity, 2B+ occurrence records. | Y | Y | gbif.org/developer/summary. |
| Natural Earth | Cartographic data — country borders, cities, rivers, 1:10M / 1:50M / 1:110M. | N | Y | naturalearthdata.com. Public domain. |
| OpenStreetMap Planet | Full world geography, 10B+ nodes. Daily diffs. | N | Y | planet.openstreetmap.org. |
| Global Surface Water (JRC) | Inland water body change 1984–2021 (Landsat). | Y | Y | Global Surface Water Explorer / GEE. |
| AERONET | Aerosol optical depth from 500+ ground stations (NASA). | Y | Y | aeronet.gsfc.nasa.gov. |
| IUCN Red List | Species conservation status for 150K+ species. | Y | Y | iucnredlist.org/resources/grid-files. Registration. |
| US Census TIGER | Geographic boundaries — states, counties, census tracts, roads. | N | Y | census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html. |
| NYC OpenData | 3000+ NYC datasets — 311, crime, taxi, permits, etc. | Y | Y | data.cityofnewyork.us. Socrata API. |
| OpenAQ | Real-time and historical air quality from 30,000+ locations. | Y | Y | api.openaq.org. |
| Global Fishing Watch | AIS-based fishing vessel tracking. | Y | Y | globalfishingwatch.org/data-download. |
| OpenSky Network | ADS-B flight tracking, 25B+ flight records. | Y | Y | opensky-network.org/data/impala-guide. |
| MarineTraffic | AIS vessel positions. | Y | N | marinetraffic.com/en/p/api-services. Subscription for bulk. |

---

## Biological / Genomics / Proteomics / Chemistry

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| UniProt | 220M+ protein sequences and annotations. | Y | Y | uniprot.org/help/api. FTP dump ~100GB. |
| Protein Data Bank (PDB) | 220K+ experimentally determined protein structures. | Y | Y | rcsb.org/docs/programmatic-access. FTP dump. |
| AlphaFold DB | 200M+ predicted protein structures (DeepMind/EMBL-EBI). | Y | Y | alphafold.ebi.ac.uk/download. Full dump ~1TB. |
| NCBI GenBank | 1T+ nucleotide bases, all public DNA sequences. | Y | Y | ncbi.nlm.nih.gov/genbank. FTP dump. |
| NCBI RefSeq | Curated reference sequences (DNA, RNA, protein). | Y | Y | ncbi.nlm.nih.gov/refseq. FTP. |
| SRA | Sequence Read Archive — raw high-throughput sequencing. 50+ petabases. | Y | Y | ncbi.nlm.nih.gov/sra. AWS Open Data. |
| GEO | Gene Expression Omnibus — 4M+ samples, microarray/RNA-seq. | Y | Y | ncbi.nlm.nih.gov/geo. FTP. |
| GTEx v10 | Gene expression across 54 human tissues, 1000 donors. | N | Y | gtexportal.org/home/downloads/adult-gtex. |
| ENCODE | Functional genomics — ChIP-seq, ATAC-seq, RNA-seq across cell types. | Y | Y | encodeproject.org/help/rest-api. |
| gnomAD v4 | Population genomics — 800K+ exomes/genomes, variant frequencies. | Y | Y | gnomad.broadinstitute.org/downloads. |
| ClinVar | 2M+ variants with clinical significance. | Y | Y | ncbi.nlm.nih.gov/clinvar. FTP. |
| dbSNP | 1B+ human SNP records. | Y | Y | ncbi.nlm.nih.gov/snp. FTP. |
| TCGA | Multi-omics cancer genomics — 33 cancer types, 11K patients. | Y | Y | portal.gdc.cancer.gov. GDC API. |
| ICGC | International Cancer Genome Consortium — 80+ cancer projects. | Y | Y | dcc.icgc.org. |
| Human Cell Atlas | Single-cell RNA-seq across all cell types (ongoing). | Y | Y | data.humancellatlas.org. |
| Allen Brain Atlas | Gene expression in mouse and human brain. | Y | Y | developingmouse.brain-map.org/api/v2/well_known_file_download. |
| ChEMBL | 2.4M+ compounds, 18M+ bioactivity records. | Y | Y | chembl.ac.uk/api. Full dump. |
| PubChem | 300M+ compounds, structures, biological activities. | Y | Y | pubchem.ncbi.nlm.nih.gov/rest/pug. FTP dump. |
| ZINC | 750M+ purchasable compounds (drug-like). | Y | Y | zinc.docking.org/tranches/all. |
| DrugBank | 15K drugs + 5M interactions. | Y | Partial | drugbank.com. Full dump requires academic registration. |
| ChemSpider | 100M+ chemical structures (RSC). | Y | N | chemspider.com/InChI.asmx. API, no bulk dump. |
| HMDB | Human Metabolome Database — 220K+ metabolites. | Y | Y | hmdb.ca/downloads. |
| KEGG | Metabolic pathways, genomes, diseases. | Y | Partial | kegg.jp/kegg/rest. Subscription for full download. |
| Reactome | Curated biological pathways. | Y | Y | reactome.org/download. |
| STRING | Protein-protein interaction network — 67M proteins. | Y | Y | string-db.org/cgi/download. |
| IntAct | Molecular interaction database. | Y | Y | ebi.ac.uk/intact/downloads. |
| ChEBI | Chemical Entities of Biological Interest — ontology. | Y | Y | ebi.ac.uk/chebi/downloadsForward.do. |
| MIMIC-III / IV | ICU clinical records — 60K / 190K hospital admissions (MIT). | N | Y | physionet.org. CITI training required. |
| PhysioNet | Physiological signals — ECG, EEG, respiration, blood pressure. | Y | Y | physionet.org/content. |
| eICU Collaborative | Multi-center ICU data, 200K+ admissions. | N | Y | physionet.org. Credentialing required. |
| UK Biobank | 500K participants — genotyping, imaging, EHR, lifestyle. | N | Y | ukbiobank.ac.uk. Application + fee required. |
| All of Us | NIH US population health cohort — 1M participants (ongoing). | N | Partial | allofus.nih.gov. Tiered access. |

---

## Financial / Economic / Legal

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| FRED | 800K+ US and international economic time series (Federal Reserve). | Y | Y | fred.stlouisfed.org/docs/api. Full download too. |
| World Bank Open Data | 16K+ development indicators, 200+ countries. | Y | Y | datahelpdesk.worldbank.org/knowledgebase/articles/889386. |
| IMF Data | Balance of payments, fiscal, financial statistics. | Y | Y | imf.org/en/Data. JSON API. |
| OECD Stats | 800+ datasets, 40+ member countries. | Y | Y | data.oecd.org. SDMX API. |
| Eurostat | EU statistical data — all domains. | Y | Y | ec.europa.eu/eurostat/web/json-and-unicode-web-services. |
| BLS (Bureau of Labor Statistics) | CPI, unemployment, wages, productivity. | Y | Y | bls.gov/developers/api_signature.htm. |
| BEA (Bureau of Economic Analysis) | GDP, personal income, trade. | Y | Y | bea.gov/API/bea_web_service_api_user_guide.htm. |
| SEC EDGAR | 40M+ financial filings — 10-K, 10-Q, 8-K, proxy. | Y | Y | efts.sec.gov. Full index bulk download. |
| UN Comtrade | International trade statistics — 200+ countries. | Y | Y | comtrade.un.org/api. |
| Our World in Data | Compiled cross-disciplinary time series (Oxford). | N | Y | ourworldindata.org/owid-grapher/datasets. GitHub. |
| Gapminder | Development indicators visualized. | N | Y | gapminder.org/data. Google Sheets + CSV. |
| Penn World Tables | GDP, productivity, trade — 183 countries, 1950–present. | N | Y | rug.nl/ggdc/productivity/pwt. |
| Maddison Project | Historical GDP reconstructions, 1 AD–present. | N | Y | rug.nl/ggdc/historicaldevelopment/maddison. |
| FEC Campaign Finance | All US campaign contributions and expenditures. | Y | Y | api.open.fec.gov. Full bulk downloads. |
| OpenSecrets | Compiled FEC data + lobbying disclosures. | Y | Partial | opensecrets.org/open-data/api-documentation. |
| CourtListener (PACER) | US federal court opinions, 4M+ documents. | Y | Y | courtlistener.com/api/rest/v4. Bulk download via recap archive. |
| EU Case Law (CVRIA) | Court of Justice of the EU — judgments and opinions. | Y | Y | curia.europa.eu/juris/recherche.jsf. EUR-Lex API. |
| LexPredict | Legal NLP datasets — contract clauses, regulatory text. | N | Y | GitHub/LexPredict. |
| GovTrack | US legislation, votes, members. | Y | Y | govtrack.us/developers/api. |
| Yahoo Finance (historical) | OHLCV stock data, historical prices. | N | N | No official API. Third-party wrappers (yfinance). robots.txt evolving. |
| Alpha Vantage | Stock, forex, crypto OHLCV — 500 req/day free. | Y | N | alphavantage.co. No free bulk dump. |
| Stooq | Daily OHLCV for stocks, indices, forex, commodities. | N | Y | stooq.com/db/h. Bulk CSV download. |
| CRSP | Center for Research in Security Prices — survivorship-free US stock data. | N | N | crsp.org. Academic license. Gold standard but expensive. |
| Compustat | Fundamental financial data for public companies. | N | N | spglobal.com. Subscription. |
| Quandl / Nasdaq Data Link | Financial, commodity, economic datasets — mix of free and paid. | Y | Partial | data.nasdaq.com/api. |
| Open Corporates | 200M+ company records globally. | Y | Partial | api.opencorporates.com. Rate-limited free tier. |

---

## Scientific / Scholarly / Bibliometric

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| OpenAlex | 240M+ scholarly works, 240M citations, authors, institutions, concepts. | Y | Y | api.openalex.org. S3 snapshot weekly. **Best open scholarly graph.** |
| Semantic Scholar ORC | 200M+ papers, citations, abstracts, author data (AI2). | Y | Y | api.semanticscholar.org. Full dataset via S3. |
| CrossRef | 145M+ DOI metadata records — titles, authors, affiliations, citations. | Y | Y | api.crossref.org. Snapshots via Academic Torrents. |
| PubMed Central OA | 4M+ full-text biomedical papers (NLM). | Y | Y | ncbi.nlm.nih.gov/pmc/tools/ftp. |
| arXiv | 2M+ preprints — physics, math, CS, bio. LaTeX source + PDF. | N | Y | arxiv.org/help/bulk_data. S3 requester-pays. |
| bioRxiv / medRxiv | Biology and medical preprints (Cold Spring Harbor). | Y | Partial | api.biorxiv.org. No full dump. |
| SSRN | Social science preprints (Elsevier). | N | N | ssrn.com. No public API or dump. |
| Dryad | Research data behind published papers. | Y | Y | datadryad.org/api/v2. |
| Zenodo | CERN open-access repository — all disciplines. | Y | Y | zenodo.org/api. OAI-PMH. 3M+ records. |
| Figshare | Academic data repository. | Y | Y | docs.figshare.com. |
| OSF (Open Science Framework) | Preprints + research data (COS). | Y | Y | api.osf.io. |
| IEEE DataPort | Engineering and technology datasets. | Y | Partial | ieee-dataport.org. Registration. |
| Harvard Dataverse | Academic data repository (Harvard). | Y | Y | dataverse.harvard.edu/api. |
| ICPSR | Social science data archive, 17K+ datasets (UMich). | Y | Y | icpsr.umich.edu/web/pages/ICPSR/index.html. Registration for some. |
| UK Data Service | Social science data — surveys, census, qualitative. | Y | Y | ukdataservice.ac.uk. Registration. |
| GESIS Data Archive | German social science data, European survey series. | Y | Y | gesis.org/en/data-services. |

---

## 3D / Point Cloud / Spatial

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| ShapeNet | 3M+ 3D CAD models, 3,000 categories (Stanford/Princeton/TTIC). | N | Y | shapenet.org. Registration. |
| ModelNet10/40 | 127K / 151K 3D CAD models, 10/40 classes. | N | Y | modelnet.cs.princeton.edu. |
| ScanNet | 2.5M views, 3D reconstructions, semantic labels, 1,513 rooms. | N | Y | scannet.is.tue.mpg.de. Registration. |
| S3DIS | Large-scale 3D indoor spaces (6 areas, 271 rooms). | N | Y | buildingparser.stanford.edu/dataset.html. |
| SemanticKITTI | LiDAR point cloud segmentation from KITTI. | N | Y | semantic-kitti.org. |
| Objaverse | 800K+ 3D objects, large-scale (Allen AI). | N | Y | objaverse.allenai.org. |
| ABO (Amazon Berkeley Objects) | 147K product 3D models with metadata. | N | Y | amazon-berkeley-objects.s3.amazonaws.com. |
| Google Scanned Objects | 1000+ household objects, photogrammetry. | N | Y | github.com/google-research/google-scanned-objects. |

---

## Social Networks / Behavioral

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| SNAP (Stanford) | Social network graph datasets — Amazon, Google, citation networks, Twitter, Reddit, Epinions. 70+ datasets. | N | Y | snap.stanford.edu/data. |
| Network Repository | 5,000+ network datasets across domains. | N | Y | networkrepository.com. |
| KONECT | Koblenz Network Collection — 260+ real-world networks. | N | Y | konect.cc. |
| MovieLens | 25M+ movie ratings, 162K users (GroupLens). | N | Y | grouplens.org/datasets/movielens. |
| Netflix Prize | 100M ratings, 480K users (historical, 2007). | N | Y | kaggle.com/netflix-inc/netflix-prize-data. |
| Goodreads (McAuley) | 15M reviews, 1.5M books (UCSD). | N | Y | mengtingwan.github.io/data/goodreads. |
| Amazon Reviews 2023 | 571M reviews across all product categories (McAuley/UCSD). | N | Y | amazon-reviews-2023.github.io. |
| Yelp Open Dataset | 7M reviews, 150K businesses, 11 cities. | N | Y | yelp.com/dataset. Annual release. |
| LastFM | Music listening history, 1B+ events, 360K users. | N | Y | HuggingFace datasets / Last.fm API. |
| Twitter (X) Academic API | Historical tweet access — partially frozen 2023. | Y | N | developer.twitter.com. API v2 academic track restricted. |
| Reddit dumps | 1B+ posts/comments via PushShift (partially archived). | N | Partial | academictorrents.com/details/c398a571976c78d346c325bd75c47b82. |
| Wikipedia Edit History | Full revision history of all articles. | N | Y | dumps.wikimedia.org. |
| GH Archive | GitHub public event stream — pushes, PRs, issues, 2011–present. | N | Y | gharchive.org. Hourly JSON. BigQuery public dataset. |

---

## Knowledge Graphs / Ontologies

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| Wikidata | 100M+ structured facts across all domains. | Y | Y | query.wikidata.org SPARQL. Dumps at dumps.wikimedia.org. |
| DBpedia | Structured data extracted from Wikipedia infoboxes. | Y | Y | wiki.dbpedia.org/develop/datasets. |
| YAGO 4.5 | Knowledge graph from Wikipedia + Wikidata + schema.org. | N | Y | yago-knowledge.org/downloads. |
| ConceptNet 5.7 | 34M commonsense facts across 37 languages. | Y | Y | conceptnet.io/downloads. |
| Freebase (Google) | 1.9B facts, donated to Wikidata 2015 (legacy dump). | N | Y | developers.google.com/freebase (archived). |
| WordNet 3.1 | English lexical database — synsets, semantic relations. | N | Y | wordnet.princeton.edu. |
| FrameNet 1.7 | Berkeley Frame Semantics — 1,221 frames, 13K lexical units. | N | Y | framenet.icsi.berkeley.edu. |
| BabelNet 5.3 | 500+ language multilingual encyclopedic network (word senses). | Y | Y | babelnet.org/download. Registration. |
| Gene Ontology (GO) | Biological process, molecular function, cellular component. | Y | Y | geneontology.org/docs/download-ontology. |
| SNOMED CT | Clinical terminology — 350K+ medical concepts. | N | Y | snomed.org. UMLS license. |
| ICD-10 / ICD-11 | International disease classification (WHO). | Y | Y | icd.who.int/browse. ICD-11 API. |
| UMLS | Unified Medical Language System — 3.5M+ biomedical concepts. | N | Y | uts.nlm.nih.gov. License required. |
| MeSH | Medical Subject Headings — 30K+ biomedical terms (NLM). | N | Y | nlm.nih.gov/mesh/meshhome.html. FTP. |
| ChEBI | Chemical Entities of Biological Interest. | Y | Y | ebi.ac.uk/chebi/downloadsForward.do. |
| OBO Foundry | 160+ interoperable biological/biomedical ontologies. | N | Y | obofoundry.org. |
| Schema.org | Structured data vocabulary used across the web. | N | Y | schema.org/docs/developers.html. |
| DOLCE / SUMO | Foundational upper ontologies. | N | Y | ontologyportal.org. |

---

## Games / Synthetic / Simulation

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| EVE Online — Project Discovery | Phase 1: exoplanet transits (TESS). Phase 2: COVID-19 proteins (HPA). Phase 3: cancer cells (Allen Institute). Players classified ~300M data points total. | N | Partial | Data published via scientific papers / CCP partnerships. Not monolithically downloadable. |
| FoldIt Solutions | Player-derived protein structures — contributed to 2011 Science paper and others. | N | Partial | fold.it/portal/info/science. Some solutions on GitHub/Zenodo. |
| OpenAI Gym / Gymnasium | Standardized RL environments (CartPole, Atari, MuJoCo). | N | Y | github.com/openai/gym. |
| DeepMind Control Suite | Physics-based continuous control tasks. | N | Y | github.com/deepmind/dm_control. |
| Atari 2600 (ALE) | 55 Atari games, pixel observations. | N | Y | atari-games.s3.amazonaws.com. |
| MineRL | Minecraft tasks with human demonstrations, 1M+ frames. | N | Y | minerl.io/dataset. |
| StarCraft II (SC2LE) | 65K replays from professional + ladder games (DeepMind/Blizzard). | N | Y | github.com/deepmind/pysc2. |
| Dota 2 OpenAI | Match telemetry from Dota 2 (OpenAI Five). | N | Partial | Limited release via OpenAI blog. |
| Lichess Games | 4B+ chess games, PGN format. Full database download. | N | Y | database.lichess.org. Monthly dumps. |
| KGS Go Games | 2M+ ranked Go games. | N | Y | u-go.net/gamerecords. |
| CARLA | Synthetic autonomous driving — photorealistic, annotated. | N | Y | carla.org. |
| AI2-THOR | Photorealistic indoor environments for embodied AI. | Y | Y | ai2thor.allenai.org. |
| Habitat / HM3D | 3D indoor environments, embodied navigation. | N | Y | aihabitat.org/datasets. |

---

## Time Series

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| UCR Time Series Archive | 128 univariate time series classification datasets. | N | Y | cs.ucr.edu/~eamonn/time_series_data_2018. |
| UEA Multivariate TS | 30 multivariate time series datasets. | N | Y | timeseriesclassification.com. |
| M1/M2/M3/M4/M5 Competitions | Forecasting competitions — thousands of series. | N | Y | forecasting-competitions.com. GitHub. |
| Monash Forecasting Repository | 30 datasets across diverse domains. | N | Y | monash.edu/research/business/forecasting-research/forecasting-repository. |
| ETDataset | Electricity transformer temperature (ETT) — multivariate. | N | Y | GitHub/zhouhaoyi/ETDataset. |
| Traffic (PEMS) | Highway sensor occupancy and speed (California). | N | Y | pems.dot.ca.gov. |
| Yahoo S5 | 367 anomaly detection time series (Yahoo). | N | Y | webscope.sandbox.yahoo.com. Registration. |
| PhysioNet Challenge | Annual time series competitions — ECG, sepsis prediction, etc. | N | Y | physionet.org/content. |

---

## Survey / Social Science / Demographics

| Dataset | Description | API | Dump | Notes |
|---------|-------------|-----|------|-------|
| US Census Bureau | Decennial census, ACS, economic surveys. | Y | Y | api.census.gov. Bulk downloads. |
| Current Population Survey | Monthly US employment/demographic survey. | N | Y | bls.gov/cps/data.htm. |
| General Social Survey (GSS) | US social attitudes, 1972–present. | N | Y | gss.norc.org/get-the-data. |
| World Values Survey | Values/beliefs in 120 countries. | N | Y | worldvaluessurvey.org/WVSDocumentationWV7.jsp. |
| Pew Research datasets | US and global opinion surveys. | N | Y | pewresearch.org/tools-and-resources/datasets. |
| NHANES | US National Health and Nutrition Examination Survey. | N | Y | cdc.gov/nchs/nhanes. |
| DHS (Demographic and Health Surveys) | Population health in 90 developing countries. | N | Y | dhsprogram.com/data. Registration. |
| IPUMS | Harmonized census and survey microdata — US and international. | Y | Y | ipums.org. Registration required. Free. |
| EU Labour Force Survey | Quarterly employment survey, EU member states. | N | Y | ec.europa.eu/eurostat/web/microdata. |
| SHARE | Survey of Health, Ageing and Retirement in Europe. | N | Y | share-project.org. Registration. |
| Luxembourg Income Study | Harmonized income/wealth microdata, 50 countries. | N | Y | lisdatacenter.org. Registration. |
| CHILDES | Child language acquisition transcripts — 130+ languages. | Y | Y | childes.talkbank.org. |

---

## Uncategorized / Cross-Domain Repositories

| Repository | Description | API | Dump | Notes |
|------------|-------------|-----|------|-------|
| UCI ML Repository | 650+ classical ML datasets — every domain. The original dataset index. | Y | Y | archive.ics.uci.edu. API added 2023. |
| OpenML | 20K+ datasets with API, auto-ML integration. | Y | Y | openml.org/api. |
| Kaggle Datasets | 250K+ user-contributed datasets. | Y | Y | kaggle.com/api/v1/datasets. CLI download. |
| HuggingFace Hub | 100K+ ML datasets — NLP, vision, audio, multimodal. | Y | Y | huggingface.co/api/datasets. |
| Zenodo | 3M+ academic deposits — all disciplines. | Y | Y | zenodo.org/api. OAI-PMH. |
| Figshare | 2M+ research data items. | Y | Y | docs.figshare.com. |
| Harvard Dataverse | 130K+ datasets (Harvard). | Y | Y | dataverse.harvard.edu/api. |
| Dryad | Data behind papers — cross-disciplinary. | Y | Y | datadryad.org/api/v2. |
| OSF Datasets | Open Science Framework — psychology, biology, social science. | Y | Y | api.osf.io. |
| IEEE DataPort | Engineering and technology — 2,700+ datasets. | Y | Partial | ieee-dataport.org. |
| data.world | 100K+ datasets, community curated. | Y | Y | data.world/developer. |
| Data.gov | 300K+ US government datasets. | Y | Y | api.data.gov. CKAN API. |
| data.europa.eu | EU open data portal. | Y | Y | data.europa.eu/api/hub. SPARQL. |
| Awesome Public Datasets (GitHub) | Curated list of 500+ datasets. | N | N | github.com/awesomedata/awesome-public-datasets. Good cross-reference. |
| Academic Torrents | 200TB+ research datasets via BitTorrent. | N | Y | academictorrents.com. The closest existing thing to PTorrent Phonebook. |
| LILA (Conservation AI) | Wildlife camera trap datasets — 20+ datasets standardized. | N | Y | lila.science. |
| Papers With Code Datasets | 10K+ ML datasets linked to benchmarks and papers. | Y | Y | paperswithcode.com/api/v1. |

---

*List status: manually compiled 2026-06-02. Verification, dump sizes, and robots.txt status to be added during automated phonebook generation. Entries without confirmed dump URLs should be crawl-verified before phonebook .ptorrent generation.*
