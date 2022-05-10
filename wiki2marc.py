import requests
import pymarc
import json
import time
from pymarc import Record, Field, MARCReader, XMLWriter
from datetime import datetime
import tempfile
import base64
import re

sparql_endpoint = "https://query.wikidata.org/sparql"

cache_wiki = {}

headers = {
	'Accept' : 'application/json',
	'User-Agent': 'App - wiki2MARC'
}


class Wiki2MARC:


	def __init__(self, **kwargs):


		self.qid = kwargs.get('qid', None)
		self.named_as = kwargs.get('named_as', None)
		self.wiki_label = None
		self.wiki_record = None
		self.marc_record = None
		self.log = []
		self.marc_as_base64 = None
		self.marc_base64_encoded = None



	def return_LC_label(self,lccn):


		url = f"https://id.loc.gov/authorities/{lccn}.skos.json"
		try:
			r = requests.get(url, headers=headers)
			if r.status_code != 200:
				self.log_add(f"Asking for json data for {lccn} recieved status code {r.status_code} cannot continue",type="error")
				return False

			data = json.loads(r.text)

		except Exception as e:
			self.log_add(f"Could not connect/query id.loc.gov",type="error",msg2=f"Error message: {str(e)}")
			return False


		for d in data:

			for key in d:

				if 'http://www.w3.org/2004/02/skos/core#prefLabel' == key:
					if lccn in d['@id'] and 'id.loc.gov' in d['@id']:

						if len(d['http://www.w3.org/2004/02/skos/core#prefLabel']) > 0:

							return d['http://www.w3.org/2004/02/skos/core#prefLabel'][0]['@value']

		return None


	def return_wikidata_field_reference(self,field,ref):

		results = []

		if field in self.wiki_record['claims']:
			for f in self.wiki_record['claims'][field]:

				if 'references' in f:

					for r in f['references']:

						if ref in r['snaks']:

							for ref_val in r['snaks'][ref]:

								value = ref_val['datavalue']['value']
								value_type = ref_val['datatype']

								if value_type == 'wikibase-item':

										l = self.return_wikidata_label(value['id'])	

										# look for a bib lccn
										b = self.return_wikidata_field('P1144',look_in=value['id'] )
										if len(b) > 0:
											b = b[0]['value']
										else:
											b = None

										
										results.append({'value':value,'wiki_type':value_type,'label':l,'lccn':b,'lccn_label':None})

								else:

									results.append({'value':value,'wiki_type':value_type,'label':None,'lccn':None,'lccn_label':None})

		return results


	def return_wikidata_label(self,qid, **kwargs):

		all_langs = kwargs.get('all_langs', None)
		langs = [{"alpha_2":"aa","alpha_3":"aar","name":"Afar"},{"alpha_2":"ab","alpha_3":"abk","name":"Abkhazian"},{"alpha_3":"ace","name":"Achinese"},{"alpha_3":"ach","name":"Acoli"},{"alpha_3":"ada","name":"Adangme"},{"alpha_3":"ady","name":"Adyghe; Adygei"},{"alpha_3":"afa","name":"Afro-Asiatic languages"},{"alpha_3":"afh","name":"Afrihili"},{"alpha_2":"af","alpha_3":"afr","name":"Afrikaans"},{"alpha_3":"ain","name":"Ainu"},{"alpha_2":"ak","alpha_3":"aka","name":"Akan"},{"alpha_3":"akk","name":"Akkadian"},{"alpha_3":"ale","name":"Aleut"},{"alpha_3":"alg","name":"Algonquian languages"},{"alpha_3":"alt","name":"Southern Altai"},{"alpha_2":"am","alpha_3":"amh","name":"Amharic"},{"alpha_3":"ang","name":"English, Old (ca. 450-1100)"},{"alpha_3":"anp","name":"Angika"},{"alpha_3":"apa","name":"Apache languages"},{"alpha_2":"ar","alpha_3":"ara","name":"Arabic"},{"alpha_3":"arc","name":"Official Aramaic (700-300 BCE); Imperial Aramaic (700-300 BCE)"},{"alpha_2":"an","alpha_3":"arg","name":"Aragonese"},{"alpha_3":"arn","name":"Mapudungun; Mapuche"},{"alpha_3":"arp","name":"Arapaho"},{"alpha_3":"art","name":"Artificial languages"},{"alpha_3":"arw","name":"Arawak"},{"alpha_2":"as","alpha_3":"asm","name":"Assamese"},{"alpha_3":"ast","name":"Asturian; Bable; Leonese; Asturleonese"},{"alpha_3":"ath","name":"Athapascan languages"},{"alpha_3":"aus","name":"Australian languages"},{"alpha_2":"av","alpha_3":"ava","name":"Avaric"},{"alpha_2":"ae","alpha_3":"ave","name":"Avestan"},{"alpha_3":"awa","name":"Awadhi"},{"alpha_2":"ay","alpha_3":"aym","name":"Aymara"},{"alpha_2":"az","alpha_3":"aze","name":"Azerbaijani"},{"alpha_3":"bad","name":"Banda languages"},{"alpha_3":"bai","name":"Bamileke languages"},{"alpha_2":"ba","alpha_3":"bak","name":"Bashkir"},{"alpha_3":"bal","name":"Baluchi"},{"alpha_2":"bm","alpha_3":"bam","name":"Bambara"},{"alpha_3":"ban","name":"Balinese"},{"alpha_3":"bas","name":"Basa"},{"alpha_3":"bat","name":"Baltic languages"},{"alpha_3":"bej","name":"Beja; Bedawiyet"},{"alpha_2":"be","alpha_3":"bel","name":"Belarusian"},{"alpha_3":"bem","name":"Bemba"},{"alpha_2":"bn","alpha_3":"ben","common_name":"Bangla","name":"Bengali"},{"alpha_3":"ber","name":"Berber languages"},{"alpha_3":"bho","name":"Bhojpuri"},{"alpha_2":"bh","alpha_3":"bih","name":"Bihari languages"},{"alpha_3":"bik","name":"Bikol"},{"alpha_3":"bin","name":"Bini; Edo"},{"alpha_2":"bi","alpha_3":"bis","name":"Bislama"},{"alpha_3":"bla","name":"Siksika"},{"alpha_3":"bnt","name":"Bantu (Other)"},{"alpha_2":"bo","alpha_3":"bod","bibliographic":"tib","name":"Tibetan"},{"alpha_2":"bs","alpha_3":"bos","name":"Bosnian"},{"alpha_3":"bra","name":"Braj"},{"alpha_2":"br","alpha_3":"bre","name":"Breton"},{"alpha_3":"btk","name":"Batak languages"},{"alpha_3":"bua","name":"Buriat"},{"alpha_3":"bug","name":"Buginese"},{"alpha_2":"bg","alpha_3":"bul","name":"Bulgarian"},{"alpha_3":"byn","name":"Blin; Bilin"},{"alpha_3":"cad","name":"Caddo"},{"alpha_3":"cai","name":"Central American Indian languages"},{"alpha_3":"car","name":"Galibi Carib"},{"alpha_2":"ca","alpha_3":"cat","name":"Catalan; Valencian"},{"alpha_3":"cau","name":"Caucasian languages"},{"alpha_3":"ceb","name":"Cebuano"},{"alpha_3":"cel","name":"Celtic languages"},{"alpha_2":"cs","alpha_3":"ces","bibliographic":"cze","name":"Czech"},{"alpha_2":"ch","alpha_3":"cha","name":"Chamorro"},{"alpha_3":"chb","name":"Chibcha"},{"alpha_2":"ce","alpha_3":"che","name":"Chechen"},{"alpha_3":"chg","name":"Chagatai"},{"alpha_3":"chk","name":"Chuukese"},{"alpha_3":"chm","name":"Mari"},{"alpha_3":"chn","name":"Chinook jargon"},{"alpha_3":"cho","name":"Choctaw"},{"alpha_3":"chp","name":"Chipewyan; Dene Suline"},{"alpha_3":"chr","name":"Cherokee"},{"alpha_2":"cu","alpha_3":"chu","name":"Church Slavic; Old Slavonic; Church Slavonic; Old Bulgarian; Old Church Slavonic"},{"alpha_2":"cv","alpha_3":"chv","name":"Chuvash"},{"alpha_3":"chy","name":"Cheyenne"},{"alpha_3":"cmc","name":"Chamic languages"},{"alpha_3":"cop","name":"Coptic"},{"alpha_2":"kw","alpha_3":"cor","name":"Cornish"},{"alpha_2":"co","alpha_3":"cos","name":"Corsican"},{"alpha_3":"cpe","name":"Creoles and pidgins, English based"},{"alpha_3":"cpf","name":"Creoles and pidgins, French-based"},{"alpha_3":"cpp","name":"Creoles and pidgins, Portuguese-based"},{"alpha_2":"cr","alpha_3":"cre","name":"Cree"},{"alpha_3":"crh","name":"Crimean Tatar; Crimean Turkish"},{"alpha_3":"crp","name":"Creoles and pidgins"},{"alpha_3":"csb","name":"Kashubian"},{"alpha_3":"cus","name":"Cushitic languages"},{"alpha_2":"cy","alpha_3":"cym","bibliographic":"wel","name":"Welsh"},{"alpha_3":"dak","name":"Dakota"},{"alpha_2":"da","alpha_3":"dan","name":"Danish"},{"alpha_3":"dar","name":"Dargwa"},{"alpha_3":"day","name":"Land Dayak languages"},{"alpha_3":"del","name":"Delaware"},{"alpha_3":"den","name":"Slave (Athapascan)"},{"alpha_2":"de","alpha_3":"deu","bibliographic":"ger","name":"German"},{"alpha_3":"dgr","name":"Dogrib"},{"alpha_3":"din","name":"Dinka"},{"alpha_2":"dv","alpha_3":"div","name":"Divehi; Dhivehi; Maldivian"},{"alpha_3":"doi","name":"Dogri"},{"alpha_3":"dra","name":"Dravidian languages"},{"alpha_3":"dsb","name":"Lower Sorbian"},{"alpha_3":"dua","name":"Duala"},{"alpha_3":"dum","name":"Dutch, Middle (ca. 1050-1350)"},{"alpha_3":"dyu","name":"Dyula"},{"alpha_2":"dz","alpha_3":"dzo","name":"Dzongkha"},{"alpha_3":"efi","name":"Efik"},{"alpha_3":"egy","name":"Egyptian (Ancient)"},{"alpha_3":"eka","name":"Ekajuk"},{"alpha_2":"el","alpha_3":"ell","bibliographic":"gre","name":"Greek, Modern (1453-)"},{"alpha_3":"elx","name":"Elamite"},{"alpha_2":"en","alpha_3":"eng","name":"English"},{"alpha_3":"enm","name":"English, Middle (1100-1500)"},{"alpha_2":"eo","alpha_3":"epo","name":"Esperanto"},{"alpha_2":"et","alpha_3":"est","name":"Estonian"},{"alpha_2":"eu","alpha_3":"eus","bibliographic":"baq","name":"Basque"},{"alpha_2":"ee","alpha_3":"ewe","name":"Ewe"},{"alpha_3":"ewo","name":"Ewondo"},{"alpha_3":"fan","name":"Fang"},{"alpha_2":"fo","alpha_3":"fao","name":"Faroese"},{"alpha_2":"fa","alpha_3":"fas","bibliographic":"per","name":"Persian"},{"alpha_3":"fat","name":"Fanti"},{"alpha_2":"fj","alpha_3":"fij","name":"Fijian"},{"alpha_3":"fil","name":"Filipino; Pilipino"},{"alpha_2":"fi","alpha_3":"fin","name":"Finnish"},{"alpha_3":"fiu","name":"Finno-Ugrian languages"},{"alpha_3":"fon","name":"Fon"},{"alpha_2":"fr","alpha_3":"fra","bibliographic":"fre","name":"French"},{"alpha_3":"frm","name":"French, Middle (ca. 1400-1600)"},{"alpha_3":"fro","name":"French, Old (842-ca. 1400)"},{"alpha_3":"frr","name":"Northern Frisian"},{"alpha_3":"frs","name":"Eastern Frisian"},{"alpha_2":"fy","alpha_3":"fry","name":"Western Frisian"},{"alpha_2":"ff","alpha_3":"ful","name":"Fulah"},{"alpha_3":"fur","name":"Friulian"},{"alpha_3":"gaa","name":"Ga"},{"alpha_3":"gay","name":"Gayo"},{"alpha_3":"gba","name":"Gbaya"},{"alpha_3":"gem","name":"Germanic languages"},{"alpha_3":"gez","name":"Geez"},{"alpha_3":"gil","name":"Gilbertese"},{"alpha_2":"gd","alpha_3":"gla","name":"Gaelic; Scottish Gaelic"},{"alpha_2":"ga","alpha_3":"gle","name":"Irish"},{"alpha_2":"gl","alpha_3":"glg","name":"Galician"},{"alpha_2":"gv","alpha_3":"glv","name":"Manx"},{"alpha_3":"gmh","name":"German, Middle High (ca. 1050-1500)"},{"alpha_3":"goh","name":"German, Old High (ca. 750-1050)"},{"alpha_3":"gon","name":"Gondi"},{"alpha_3":"gor","name":"Gorontalo"},{"alpha_3":"got","name":"Gothic"},{"alpha_3":"grb","name":"Grebo"},{"alpha_3":"grc","name":"Greek, Ancient (to 1453)"},{"alpha_2":"gn","alpha_3":"grn","name":"Guarani"},{"alpha_3":"gsw","name":"Swiss German; Alemannic; Alsatian"},{"alpha_2":"gu","alpha_3":"guj","name":"Gujarati"},{"alpha_3":"gwi","name":"Gwich'in"},{"alpha_3":"hai","name":"Haida"},{"alpha_2":"ht","alpha_3":"hat","name":"Haitian; Haitian Creole"},{"alpha_2":"ha","alpha_3":"hau","name":"Hausa"},{"alpha_3":"haw","name":"Hawaiian"},{"alpha_2":"he","alpha_3":"heb","name":"Hebrew"},{"alpha_2":"hz","alpha_3":"her","name":"Herero"},{"alpha_3":"hil","name":"Hiligaynon"},{"alpha_3":"him","name":"Himachali languages; Western Pahari languages"},{"alpha_2":"hi","alpha_3":"hin","name":"Hindi"},{"alpha_3":"hit","name":"Hittite"},{"alpha_3":"hmn","name":"Hmong; Mong"},{"alpha_2":"ho","alpha_3":"hmo","name":"Hiri Motu"},{"alpha_2":"hr","alpha_3":"hrv","name":"Croatian"},{"alpha_3":"hsb","name":"Upper Sorbian"},{"alpha_2":"hu","alpha_3":"hun","name":"Hungarian"},{"alpha_3":"hup","name":"Hupa"},{"alpha_2":"hy","alpha_3":"hye","bibliographic":"arm","name":"Armenian"},{"alpha_3":"iba","name":"Iban"},{"alpha_2":"ig","alpha_3":"ibo","name":"Igbo"},{"alpha_2":"io","alpha_3":"ido","name":"Ido"},{"alpha_2":"ii","alpha_3":"iii","name":"Sichuan Yi; Nuosu"},{"alpha_3":"ijo","name":"Ijo languages"},{"alpha_2":"iu","alpha_3":"iku","name":"Inuktitut"},{"alpha_2":"ie","alpha_3":"ile","name":"Interlingue; Occidental"},{"alpha_3":"ilo","name":"Iloko"},{"alpha_2":"ia","alpha_3":"ina","name":"Interlingua (International Auxiliary Language Association)"},{"alpha_3":"inc","name":"Indic languages"},{"alpha_2":"id","alpha_3":"ind","name":"Indonesian"},{"alpha_3":"ine","name":"Indo-European languages"},{"alpha_3":"inh","name":"Ingush"},{"alpha_2":"ik","alpha_3":"ipk","name":"Inupiaq"},{"alpha_3":"ira","name":"Iranian languages"},{"alpha_3":"iro","name":"Iroquoian languages"},{"alpha_2":"is","alpha_3":"isl","bibliographic":"ice","name":"Icelandic"},{"alpha_2":"it","alpha_3":"ita","name":"Italian"},{"alpha_2":"jv","alpha_3":"jav","name":"Javanese"},{"alpha_3":"jbo","name":"Lojban"},{"alpha_2":"ja","alpha_3":"jpn","name":"Japanese"},{"alpha_3":"jpr","name":"Judeo-Persian"},{"alpha_3":"jrb","name":"Judeo-Arabic"},{"alpha_3":"kaa","name":"Kara-Kalpak"},{"alpha_3":"kab","name":"Kabyle"},{"alpha_3":"kac","name":"Kachin; Jingpho"},{"alpha_2":"kl","alpha_3":"kal","name":"Kalaallisut; Greenlandic"},{"alpha_3":"kam","name":"Kamba"},{"alpha_2":"kn","alpha_3":"kan","name":"Kannada"},{"alpha_3":"kar","name":"Karen languages"},{"alpha_2":"ks","alpha_3":"kas","name":"Kashmiri"},{"alpha_2":"ka","alpha_3":"kat","bibliographic":"geo","name":"Georgian"},{"alpha_2":"kr","alpha_3":"kau","name":"Kanuri"},{"alpha_3":"kaw","name":"Kawi"},{"alpha_2":"kk","alpha_3":"kaz","name":"Kazakh"},{"alpha_3":"kbd","name":"Kabardian"},{"alpha_3":"kha","name":"Khasi"},{"alpha_3":"khi","name":"Khoisan languages"},{"alpha_2":"km","alpha_3":"khm","name":"Central Khmer"},{"alpha_3":"kho","name":"Khotanese; Sakan"},{"alpha_2":"ki","alpha_3":"kik","name":"Kikuyu; Gikuyu"},{"alpha_2":"rw","alpha_3":"kin","name":"Kinyarwanda"},{"alpha_2":"ky","alpha_3":"kir","name":"Kirghiz; Kyrgyz"},{"alpha_3":"kmb","name":"Kimbundu"},{"alpha_3":"kok","name":"Konkani"},{"alpha_2":"kv","alpha_3":"kom","name":"Komi"},{"alpha_2":"kg","alpha_3":"kon","name":"Kongo"},{"alpha_2":"ko","alpha_3":"kor","name":"Korean"},{"alpha_3":"kos","name":"Kosraean"},{"alpha_3":"kpe","name":"Kpelle"},{"alpha_3":"krc","name":"Karachay-Balkar"},{"alpha_3":"krl","name":"Karelian"},{"alpha_3":"kro","name":"Kru languages"},{"alpha_3":"kru","name":"Kurukh"},{"alpha_2":"kj","alpha_3":"kua","name":"Kuanyama; Kwanyama"},{"alpha_3":"kum","name":"Kumyk"},{"alpha_2":"ku","alpha_3":"kur","name":"Kurdish"},{"alpha_3":"kut","name":"Kutenai"},{"alpha_3":"lad","name":"Ladino"},{"alpha_3":"lah","name":"Lahnda"},{"alpha_3":"lam","name":"Lamba"},{"alpha_2":"lo","alpha_3":"lao","name":"Lao"},{"alpha_2":"la","alpha_3":"lat","name":"Latin"},{"alpha_2":"lv","alpha_3":"lav","name":"Latvian"},{"alpha_3":"lez","name":"Lezghian"},{"alpha_2":"li","alpha_3":"lim","name":"Limburgan; Limburger; Limburgish"},{"alpha_2":"ln","alpha_3":"lin","name":"Lingala"},{"alpha_2":"lt","alpha_3":"lit","name":"Lithuanian"},{"alpha_3":"lol","name":"Mongo"},{"alpha_3":"loz","name":"Lozi"},{"alpha_2":"lb","alpha_3":"ltz","name":"Luxembourgish; Letzeburgesch"},{"alpha_3":"lua","name":"Luba-Lulua"},{"alpha_2":"lu","alpha_3":"lub","name":"Luba-Katanga"},{"alpha_2":"lg","alpha_3":"lug","name":"Ganda"},{"alpha_3":"lui","name":"Luiseno"},{"alpha_3":"lun","name":"Lunda"},{"alpha_3":"luo","name":"Luo (Kenya and Tanzania)"},{"alpha_3":"lus","name":"Lushai"},{"alpha_3":"mad","name":"Madurese"},{"alpha_3":"mag","name":"Magahi"},{"alpha_2":"mh","alpha_3":"mah","name":"Marshallese"},{"alpha_3":"mai","name":"Maithili"},{"alpha_3":"mak","name":"Makasar"},{"alpha_2":"ml","alpha_3":"mal","name":"Malayalam"},{"alpha_3":"man","name":"Mandingo"},{"alpha_3":"map","name":"Austronesian languages"},{"alpha_2":"mr","alpha_3":"mar","name":"Marathi"},{"alpha_3":"mas","name":"Masai"},{"alpha_3":"mdf","name":"Moksha"},{"alpha_3":"mdr","name":"Mandar"},{"alpha_3":"men","name":"Mende"},{"alpha_3":"mga","name":"Irish, Middle (900-1200)"},{"alpha_3":"mic","name":"Mi'kmaq; Micmac"},{"alpha_3":"min","name":"Minangkabau"},{"alpha_3":"mis","name":"Uncoded languages"},{"alpha_2":"mk","alpha_3":"mkd","bibliographic":"mac","name":"Macedonian"},{"alpha_3":"mkh","name":"Mon-Khmer languages"},{"alpha_2":"mg","alpha_3":"mlg","name":"Malagasy"},{"alpha_2":"mt","alpha_3":"mlt","name":"Maltese"},{"alpha_3":"mnc","name":"Manchu"},{"alpha_3":"mni","name":"Manipuri"},{"alpha_3":"mno","name":"Manobo languages"},{"alpha_3":"moh","name":"Mohawk"},{"alpha_2":"mn","alpha_3":"mon","name":"Mongolian"},{"alpha_3":"mos","name":"Mossi"},{"alpha_2":"mi","alpha_3":"mri","bibliographic":"mao","name":"Maori"},{"alpha_2":"ms","alpha_3":"msa","bibliographic":"may","name":"Malay"},{"alpha_3":"mul","name":"Multiple languages"},{"alpha_3":"mun","name":"Munda languages"},{"alpha_3":"mus","name":"Creek"},{"alpha_3":"mwl","name":"Mirandese"},{"alpha_3":"mwr","name":"Marwari"},{"alpha_2":"my","alpha_3":"mya","bibliographic":"bur","name":"Burmese"},{"alpha_3":"myn","name":"Mayan languages"},{"alpha_3":"myv","name":"Erzya"},{"alpha_3":"nah","name":"Nahuatl languages"},{"alpha_3":"nai","name":"North American Indian languages"},{"alpha_3":"nap","name":"Neapolitan"},{"alpha_2":"na","alpha_3":"nau","name":"Nauru"},{"alpha_2":"nv","alpha_3":"nav","name":"Navajo; Navaho"},{"alpha_2":"nr","alpha_3":"nbl","name":"Ndebele, South; South Ndebele"},{"alpha_2":"nd","alpha_3":"nde","name":"Ndebele, North; North Ndebele"},{"alpha_2":"ng","alpha_3":"ndo","name":"Ndonga"},{"alpha_3":"nds","name":"Low German; Low Saxon; German, Low; Saxon, Low"},{"alpha_2":"ne","alpha_3":"nep","name":"Nepali"},{"alpha_3":"new","name":"Nepal Bhasa; Newari"},{"alpha_3":"nia","name":"Nias"},{"alpha_3":"nic","name":"Niger-Kordofanian languages"},{"alpha_3":"niu","name":"Niuean"},{"alpha_2":"nl","alpha_3":"nld","bibliographic":"dut","name":"Dutch; Flemish"},{"alpha_2":"nn","alpha_3":"nno","name":"Norwegian Nynorsk; Nynorsk, Norwegian"},{"alpha_2":"nb","alpha_3":"nob","name":"Bokmål, Norwegian; Norwegian Bokmål"},{"alpha_3":"nog","name":"Nogai"},{"alpha_3":"non","name":"Norse, Old"},{"alpha_2":"no","alpha_3":"nor","name":"Norwegian"},{"alpha_3":"nqo","name":"N'Ko"},{"alpha_3":"nso","name":"Pedi; Sepedi; Northern Sotho"},{"alpha_3":"nub","name":"Nubian languages"},{"alpha_3":"nwc","name":"Classical Newari; Old Newari; Classical Nepal Bhasa"},{"alpha_2":"ny","alpha_3":"nya","name":"Chichewa; Chewa; Nyanja"},{"alpha_3":"nym","name":"Nyamwezi"},{"alpha_3":"nyn","name":"Nyankole"},{"alpha_3":"nyo","name":"Nyoro"},{"alpha_3":"nzi","name":"Nzima"},{"alpha_2":"oc","alpha_3":"oci","name":"Occitan (post 1500); Provençal"},{"alpha_2":"oj","alpha_3":"oji","name":"Ojibwa"},{"alpha_2":"or","alpha_3":"ori","name":"Oriya"},{"alpha_2":"om","alpha_3":"orm","name":"Oromo"},{"alpha_3":"osa","name":"Osage"},{"alpha_2":"os","alpha_3":"oss","name":"Ossetian; Ossetic"},{"alpha_3":"ota","name":"Turkish, Ottoman (1500-1928)"},{"alpha_3":"oto","name":"Otomian languages"},{"alpha_3":"paa","name":"Papuan languages"},{"alpha_3":"pag","name":"Pangasinan"},{"alpha_3":"pal","name":"Pahlavi"},{"alpha_3":"pam","name":"Pampanga; Kapampangan"},{"alpha_2":"pa","alpha_3":"pan","name":"Panjabi; Punjabi"},{"alpha_3":"pap","name":"Papiamento"},{"alpha_3":"pau","name":"Palauan"},{"alpha_3":"peo","name":"Persian, Old (ca. 600-400 B.C.)"},{"alpha_3":"phi","name":"Philippine languages"},{"alpha_3":"phn","name":"Phoenician"},{"alpha_2":"pi","alpha_3":"pli","name":"Pali"},{"alpha_2":"pl","alpha_3":"pol","name":"Polish"},{"alpha_3":"pon","name":"Pohnpeian"},{"alpha_2":"pt","alpha_3":"por","name":"Portuguese"},{"alpha_3":"pra","name":"Prakrit languages"},{"alpha_3":"pro","name":"Provençal, Old (to 1500)"},{"alpha_2":"ps","alpha_3":"pus","name":"Pushto; Pashto"},{"alpha_3":"qaa-qtz","name":"Reserved for local use"},{"alpha_2":"qu","alpha_3":"que","name":"Quechua"},{"alpha_3":"raj","name":"Rajasthani"},{"alpha_3":"rap","name":"Rapanui"},{"alpha_3":"rar","name":"Rarotongan; Cook Islands Maori"},{"alpha_3":"roa","name":"Romance languages"},{"alpha_2":"rm","alpha_3":"roh","name":"Romansh"},{"alpha_3":"rom","name":"Romany"},{"alpha_2":"ro","alpha_3":"ron","bibliographic":"rum","name":"Romanian; Moldavian; Moldovan"},{"alpha_2":"rn","alpha_3":"run","name":"Rundi"},{"alpha_3":"rup","name":"Aromanian; Arumanian; Macedo-Romanian"},{"alpha_2":"ru","alpha_3":"rus","name":"Russian"},{"alpha_3":"sad","name":"Sandawe"},{"alpha_2":"sg","alpha_3":"sag","name":"Sango"},{"alpha_3":"sah","name":"Yakut"},{"alpha_3":"sai","name":"South American Indian (Other)"},{"alpha_3":"sal","name":"Salishan languages"},{"alpha_3":"sam","name":"Samaritan Aramaic"},{"alpha_2":"sa","alpha_3":"san","name":"Sanskrit"},{"alpha_3":"sas","name":"Sasak"},{"alpha_3":"sat","name":"Santali"},{"alpha_3":"scn","name":"Sicilian"},{"alpha_3":"sco","name":"Scots"},{"alpha_3":"sel","name":"Selkup"},{"alpha_3":"sem","name":"Semitic languages"},{"alpha_3":"sga","name":"Irish, Old (to 900)"},{"alpha_3":"sgn","name":"Sign Languages"},{"alpha_3":"shn","name":"Shan"},{"alpha_3":"sid","name":"Sidamo"},{"alpha_2":"si","alpha_3":"sin","name":"Sinhala; Sinhalese"},{"alpha_3":"sio","name":"Siouan languages"},{"alpha_3":"sit","name":"Sino-Tibetan languages"},{"alpha_3":"sla","name":"Slavic languages"},{"alpha_2":"sk","alpha_3":"slk","bibliographic":"slo","name":"Slovak"},{"alpha_2":"sl","alpha_3":"slv","name":"Slovenian"},{"alpha_3":"sma","name":"Southern Sami"},{"alpha_2":"se","alpha_3":"sme","name":"Northern Sami"},{"alpha_3":"smi","name":"Sami languages"},{"alpha_3":"smj","name":"Lule Sami"},{"alpha_3":"smn","name":"Inari Sami"},{"alpha_2":"sm","alpha_3":"smo","name":"Samoan"},{"alpha_3":"sms","name":"Skolt Sami"},{"alpha_2":"sn","alpha_3":"sna","name":"Shona"},{"alpha_2":"sd","alpha_3":"snd","name":"Sindhi"},{"alpha_3":"snk","name":"Soninke"},{"alpha_3":"sog","name":"Sogdian"},{"alpha_2":"so","alpha_3":"som","name":"Somali"},{"alpha_3":"son","name":"Songhai languages"},{"alpha_2":"st","alpha_3":"sot","name":"Sotho, Southern"},{"alpha_2":"es","alpha_3":"spa","name":"Spanish; Castilian"},{"alpha_2":"sq","alpha_3":"sqi","bibliographic":"alb","name":"Albanian"},{"alpha_2":"sc","alpha_3":"srd","name":"Sardinian"},{"alpha_3":"srn","name":"Sranan Tongo"},{"alpha_2":"sr","alpha_3":"srp","name":"Serbian"},{"alpha_3":"srr","name":"Serer"},{"alpha_3":"ssa","name":"Nilo-Saharan languages"},{"alpha_2":"ss","alpha_3":"ssw","name":"Swati"},{"alpha_3":"suk","name":"Sukuma"},{"alpha_2":"su","alpha_3":"sun","name":"Sundanese"},{"alpha_3":"sus","name":"Susu"},{"alpha_3":"sux","name":"Sumerian"},{"alpha_2":"sw","alpha_3":"swa","name":"Swahili"},{"alpha_2":"sv","alpha_3":"swe","name":"Swedish"},{"alpha_3":"syc","name":"Classical Syriac"},{"alpha_3":"syr","name":"Syriac"},{"alpha_2":"ty","alpha_3":"tah","name":"Tahitian"},{"alpha_3":"tai","name":"Tai languages"},{"alpha_2":"ta","alpha_3":"tam","name":"Tamil"},{"alpha_2":"tt","alpha_3":"tat","name":"Tatar"},{"alpha_2":"te","alpha_3":"tel","name":"Telugu"},{"alpha_3":"tem","name":"Timne"},{"alpha_3":"ter","name":"Tereno"},{"alpha_3":"tet","name":"Tetum"},{"alpha_2":"tg","alpha_3":"tgk","name":"Tajik"},{"alpha_2":"tl","alpha_3":"tgl","name":"Tagalog"},{"alpha_2":"th","alpha_3":"tha","name":"Thai"},{"alpha_3":"tig","name":"Tigre"},{"alpha_2":"ti","alpha_3":"tir","name":"Tigrinya"},{"alpha_3":"tiv","name":"Tiv"},{"alpha_3":"tkl","name":"Tokelau"},{"alpha_3":"tlh","name":"Klingon; tlhIngan-Hol"},{"alpha_3":"tli","name":"Tlingit"},{"alpha_3":"tmh","name":"Tamashek"},{"alpha_3":"tog","name":"Tonga (Nyasa)"},{"alpha_2":"to","alpha_3":"ton","name":"Tonga (Tonga Islands)"},{"alpha_3":"tpi","name":"Tok Pisin"},{"alpha_3":"tsi","name":"Tsimshian"},{"alpha_2":"tn","alpha_3":"tsn","name":"Tswana"},{"alpha_2":"ts","alpha_3":"tso","name":"Tsonga"},{"alpha_2":"tk","alpha_3":"tuk","name":"Turkmen"},{"alpha_3":"tum","name":"Tumbuka"},{"alpha_3":"tup","name":"Tupi languages"},{"alpha_2":"tr","alpha_3":"tur","name":"Turkish"},{"alpha_3":"tut","name":"Altaic languages"},{"alpha_3":"tvl","name":"Tuvalu"},{"alpha_2":"tw","alpha_3":"twi","name":"Twi"},{"alpha_3":"tyv","name":"Tuvinian"},{"alpha_3":"udm","name":"Udmurt"},{"alpha_3":"uga","name":"Ugaritic"},{"alpha_2":"ug","alpha_3":"uig","name":"Uighur; Uyghur"},{"alpha_2":"uk","alpha_3":"ukr","name":"Ukrainian"},{"alpha_3":"umb","name":"Umbundu"},{"alpha_3":"und","name":"Undetermined"},{"alpha_2":"ur","alpha_3":"urd","name":"Urdu"},{"alpha_2":"uz","alpha_3":"uzb","name":"Uzbek"},{"alpha_3":"vai","name":"Vai"},{"alpha_2":"ve","alpha_3":"ven","name":"Venda"},{"alpha_2":"vi","alpha_3":"vie","name":"Vietnamese"},{"alpha_2":"vo","alpha_3":"vol","name":"Volapük"},{"alpha_3":"vot","name":"Votic"},{"alpha_3":"wak","name":"Wakashan languages"},{"alpha_3":"wal","name":"Walamo"},{"alpha_3":"war","name":"Waray"},{"alpha_3":"was","name":"Washo"},{"alpha_3":"wen","name":"Sorbian languages"},{"alpha_2":"wa","alpha_3":"wln","name":"Walloon"},{"alpha_2":"wo","alpha_3":"wol","name":"Wolof"},{"alpha_3":"xal","name":"Kalmyk; Oirat"},{"alpha_2":"xh","alpha_3":"xho","name":"Xhosa"},{"alpha_3":"yao","name":"Yao"},{"alpha_3":"yap","name":"Yapese"},{"alpha_2":"yi","alpha_3":"yid","name":"Yiddish"},{"alpha_2":"yo","alpha_3":"yor","name":"Yoruba"},{"alpha_3":"ypk","name":"Yupik languages"},{"alpha_3":"zap","name":"Zapotec"},{"alpha_3":"zbl","name":"Blissymbols; Blissymbolics; Bliss"},{"alpha_3":"zen","name":"Zenaga"},{"alpha_3":"zgh","name":"Standard Moroccan Tamazight"},{"alpha_2":"za","alpha_3":"zha","name":"Zhuang; Chuang"},{"alpha_2":"zh","alpha_3":"zho","bibliographic":"chi","name":"Chinese"},{"alpha_3":"znd","name":"Zande languages"},{"alpha_2":"zu","alpha_3":"zul","name":"Zulu"},{"alpha_3":"zun","name":"Zuni"},{"alpha_3":"zxx","name":"No linguistic content; Not applicable"},{"alpha_3":"zza","name":"Zaza; Dimili; Dimli; Kirdki; Kirmanjki; Zazaki"}]


		data = None

		if qid in cache_wiki:
			data = cache_wiki[qid]

		else:

			# request it

			url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"


			try:
				r = requests.get(url, headers=headers)
				if r.status_code != 200:
					self.log_add(f"Asking for json data for {qid} recieved status code {r.status_code} cannot continue",type="error")
					return False

			except Exception as e:
				self.log_add(f"Could not connect/query wikidata",type="error",msg2=f"Error message: {str(e)}")
				return False

			try:
				data = json.loads(r.text)
			except Exception as e:
				self.log_add(f"Could not decode response from wikidata",type="error",msg2=f"Response: {r.text}")
				return False

			try:
				data = data['entities'][qid]
			except:
				self.log_add(f"Could not parse the data for this item",type="error",msg2=f"Response: {json.dumps(data,indent=2)}")
				return False

			cache_wiki[qid] = data


		if all_langs == True:

			lang_results = []

			lang_name = None
			lang_code = None

			for lang_key in data['labels']:

				for l in langs:
					if len(lang_key) == 2:
						if 'alpha_2' in l:

							if l['alpha_2'] == lang_key:
								lang_name= l['name']
								lang_code = l
								break
					elif len(lang_key) == 3:
						if 'alpha_3' in l:
							if l['alpha_3'] == lang_key:
								lang_name= l['name']
								lang_code = l
								break


				
				
				if lang_name != None:

					lang_results.append({'lang':lang_name,'lang_code':lang_key,'value':data['labels'][lang_key]['value']})


			return lang_results




		if 'en' in data['labels']:
			return data['labels']['en']['value']
		else:
			# just take the first one if en not avaiable
			return data['labels'][list(data['labels'].keys())[0]]['value']






	def return_wikidata_field(self,field, **kwargs):

		results = []

		# by default use THIS wikidata record, but you can
		# pass it another wikidata json and it will look in that one
		look_in = kwargs.get('look_in', self.wiki_record)

		if look_in == None:
			look_in = self.wiki_record


		# if it passed it just a Q id download it
		if isinstance(look_in, str) == True:



			if look_in in cache_wiki:
				look_in = cache_wiki[look_in]

			else:



				url = f"https://www.wikidata.org/wiki/Special:EntityData/{look_in}.json"


				try:
					r = requests.get(url, headers=headers)
					if r.status_code != 200:
						self.log_add(f"Asking for json data for {look_in} recieved status code {r.status_code} cannot continue",type="error")
						return False

				except Exception as e:
					self.log_add(f"Could not connect/query wikidata",type="error",msg2=f"Error message: {str(e)}")
					return False

				try:
					data = json.loads(r.text)
				except Exception as e:
					self.log_add(f"Could not decode response from wikidata",type="error",msg2=f"Response: {r.text}")
					return False

				try:
					data = data['entities'][look_in]
				except:
					self.log_add(f"Could not parse the data for this item",type="error",msg2=f"Response: {json.dumps(data,indent=2)}")
					return False

				cache_wiki[look_in] = data

				look_in = data



		# simply see if we have that field
		if field in look_in['claims']:
			self.log_add(f"Found field {field} in the wiki record", msg2=f"{json.dumps(look_in['claims'][field],indent=2)}")

			for f in look_in['claims'][field]:

				wiki_type = f['mainsnak']['datatype']
				wiki_value = f['mainsnak']['datavalue']['value']

				if wiki_type == 'wikibase-item':

					l = None
					# get the label of the the thing linked
					l = self.return_wikidata_label(wiki_value['id'])	

					lccn = None

					# look for a lccn (TODO other LC auths)
					lccn = self.return_wikidata_field('P244',look_in=wiki_value['id'] )
					if len(lccn) > 0:
						lccn = lccn[0]['value']
					else:
						lccn = None

					lccn_label = None

					if lccn != None:
						lccn_label = self.return_LC_label(lccn)



					lcdgt = self.return_wikidata_field('P4946',look_in=wiki_value['id'] )
					if len(lcdgt) > 0:
						lcdgt = lcdgt[0]['value']
					else:
						lcdgt = None

					lcdgt_label = None

					if lcdgt != None:
						lcdgt_label = self.return_LC_label(lcdgt)




					if lccn == None and lcdgt == None:
						self.log_add(f'Could not use LC number for the wikidata item {l} ({wiki_value["id"]}) because it is not mapped to a LC vocab (lcsh, naf, lcdgt, etc..)', type='warning')





					results.append({'value':wiki_value,'wiki_type':wiki_type,'label':l,'lccn':lccn,'lccn_label':lccn_label, 'lcdgt_label':lcdgt_label, 'lcdgt':lcdgt})

				elif wiki_type == 'external-id' and (field == 'P244' or field == 'P4946'):


					lccn = wiki_value
					lccn_label = self.return_LC_label(wiki_value)

					results.append({'value':wiki_value,'wiki_type':wiki_type,'label':None,'lccn':lccn,'lccn_label':lccn_label})



				else:
					results.append({'value':wiki_value,'wiki_type':wiki_type,'label':None,'lccn':None,'lccn_label':None})


		else:
			self.log_add(f"Did NOT find field {field} in the wiki record")



		return results


	def util_lccn_space(self,lccn):

		alpha = ""
		numeric = ""

		lccn = lccn.strip()

		if not lccn[0].isdigit() and not lccn[1].isdigit() and not lccn[2].isdigit() :
			alpha = lccn[0:3]
			numeric = lccn[3:]


		elif not lccn[0].isdigit() and not lccn[1].isdigit():
			alpha = lccn[0:2]
			numeric = lccn[2:]

		elif not lccn[0].isdigit():
			alpha = lccn[0]
			numeric = lccn[1:]

		# somethings not right
		else:
			return lccn



		newlccn = lccn

		if len(numeric) == 8:


			message = alpha
			fill = ' '
			align = '<'
			width = 3
			newalpha = f'{message:{fill}{align}{width}}'

			newlccn = f"{newalpha}{numeric} "


		else:

			message = alpha
			fill = ' '
			align = '<'
			width = 2
			newalpha = f'{message:{fill}{align}{width}}'
			newlccn = f"{newalpha}{numeric}"





		return newlccn


	def build_1xx(self):

		self.log_add(f"Building the 1xx fields")

		# if we have named_as just use that
		use_100 = None
		if self.named_as != None:
			use_100 = self.named_as
		else:

			# try to get it
			values = self.return_wikidata_field('P244')
			print(values)
			if len(values)>0:
				if values[0]['lccn_label'] != False:
					use_100 = values[0]['lccn_label']


			if use_100 == None:

				# see if it is at the record level
				values = self.return_wikidata_field('P1810')
				if len(values)>0:
					if values[0]['value'] != None:
						use_100 = values[0]['value']



		if use_100 == None:

			wiki_label = self.return_wikidata_label(self.qid)

			use_100 = wiki_label + ' - NOT DIRECT ORDER -'



		# look for the lccn 
		values = self.return_wikidata_field('P244')
		if len(values)>0:
			lccn = self.util_lccn_space(values[0]['value'])


			field = Field(
				tag = '010',
				indicators = [' ',' '],
				subfields = [
					'a', lccn
			])

			self.marc_record.add_field(field)



		values = self.return_wikidata_field('P957')
		if len(values)>0:

			if isinstance(values[0]['value'], str) == True: 
				
				field = Field(
					tag = '020',
					indicators = [' ',' '],
					subfields = [
						'a', values[0]['value']
				])
				self.marc_record.add_field(field)
			else:
				self.log('P957 was not a string?',type='warning',msg2=f"{json.dumps(values[0]['value'])}")

		values = self.return_wikidata_field('P212')
		if len(values)>0:

			if isinstance(values[0]['value'], str) == True: 
				
				field = Field(
					tag = '020',
					indicators = [' ',' '],
					subfields = [
						'a', values[0]['value']
				])
				self.marc_record.add_field(field)
			else:
				self.log('P212 was not a string?',type='warning',msg2=f"{json.dumps(values[0]['value'])}")


		values = self.return_wikidata_field('P236')
		if len(values)>0:

			if isinstance(values[0]['value'], str) == True: 
				
				field = Field(
					tag = '022',
					indicators = [' ',' '],
					subfields = [
						'a', values[0]['value']
				])
				self.marc_record.add_field(field)
			else:
				self.log('P236 was not a string?',type='warning',msg2=f"{json.dumps(values[0]['value'])}")


		values = self.return_wikidata_field('P213')
		if len(values)>0:

			if isinstance(values[0]['value'], str) == True: 
				
				field = Field(
					tag = '024',
					indicators = [' ',' '],
					subfields = [
						'a', values[0]['value'],
						'2', 'isni'
				])
				self.marc_record.add_field(field)
			else:
				self.log('P213 was not a string?',type='warning',msg2=f"{json.dumps(values[0]['value'])}")


		values = self.return_wikidata_field('P214')
		if len(values)>0:

			if isinstance(values[0]['value'], str) == True: 
				
				field = Field(
					tag = '024',
					indicators = [' ',' '],
					subfields = [
						'a', values[0]['value'],
						'2', 'viaf'
				])
				self.marc_record.add_field(field)
			else:
				self.log('P214 was not a string?',type='warning',msg2=f"{json.dumps(values[0]['value'])}")

		values = self.return_wikidata_field('P245')
		if len(values)>0:

			if isinstance(values[0]['value'], str) == True: 
				
				field = Field(
					tag = '024',
					indicators = [' ',' '],
					subfields = [
						'a', values[0]['value'],
						'2', 'gettyulan'
				])
				self.marc_record.add_field(field)
			else:
				self.log('P245 was not a string?',type='warning',msg2=f"{json.dumps(values[0]['value'])}")

		values = self.return_wikidata_field('P496')
		if len(values)>0:

			if isinstance(values[0]['value'], str) == True: 
				
				field = Field(
					tag = '024',
					indicators = [' ',' '],
					subfields = [
						'a', values[0]['value'],
						'2', 'orcid'
				])
				self.marc_record.add_field(field)
			else:
				self.log('P496 was not a string?',type='warning',msg2=f"{json.dumps(values[0]['value'])}")

		values = self.return_wikidata_field('P1566')
		if len(values)>0:

			if isinstance(values[0]['value'], str) == True: 
				
				field = Field(
					tag = '024',
					indicators = [' ',' '],
					subfields = [
						'a', values[0]['value'],
						'2', 'geonames'
				])
				self.marc_record.add_field(field)
			else:
				self.log('P1566 was not a string?',type='warning',msg2=f"{json.dumps(values[0]['value'])}")

		values = self.return_wikidata_field('P1566')
		if len(values)>0:

			if isinstance(values[0]['value'], str) == True: 
				
				field = Field(
					tag = '024',
					indicators = [' ',' '],
					subfields = [
						'a', values[0]['value'],
						'2', 'gettytgn'
				])
				self.marc_record.add_field(field)
			else:
				self.log('P1566 was not a string?',type='warning',msg2=f"{json.dumps(values[0]['value'])}")

		values = self.return_wikidata_field('P435')
		if len(values)>0:

			if isinstance(values[0]['value'], str) == True: 
				
				field = Field(
					tag = '024',
					indicators = [' ',' '],
					subfields = [
						'a', values[0]['value'],
						'2', 'musicb'
				])
				self.marc_record.add_field(field)
			else:
				self.log('P435 was not a string?',type='warning',msg2=f"{json.dumps(values[0]['value'])}")

		values = self.return_wikidata_field('P1617')
		if len(values)>0:

			if isinstance(values[0]['value'], str) == True: 
				
				field = Field(
					tag = '024',
					indicators = [' ',' '],
					subfields = [
						'a', values[0]['value'],
						'2', 'bbcth'
				])
				self.marc_record.add_field(field)
			else:
				self.log('P1617 was not a string?',type='warning',msg2=f"{json.dumps(values[0]['value'])}")

		values = self.return_wikidata_field('P2163')
		if len(values)>0:

			if isinstance(values[0]['value'], str) == True: 
				
				field = Field(
					tag = '024',
					indicators = [' ',' '],
					subfields = [
						'a', values[0]['value'],
						'2', 'fast'
				])
				self.marc_record.add_field(field)
			else:
				self.log('P2163 was not a string?',type='warning',msg2=f"{json.dumps(values[0]['value'])}")


		field = Field(
			tag = '024',
			indicators = [' ',' '],
			subfields = [
				'a', self.qid,
				'2', 'wikidata'
		])
		self.marc_record.add_field(field)
    

		lifedates_subfields = []
		birth_year = None

		values = self.return_wikidata_field('P569')
		if len(values)>0:


			if isinstance(values[0]['value']['time'], str) == True: 
				
				values[0]['value']['time'] = values[0]['value']['time'].split('T')[0].replace('+','')
					
				lifedates_subfields.append('f')
				lifedates_subfields.append(values[0]['value']['time'])

				if len(values[0]['value']['time'].split('-')) == 3:
					birth_year = values[0]['value']['time'].split('-')[0]



			else:
				self.log('P569 was not a string?',type='warning',msg2=f"{json.dumps(values[0]['value'])}")


		# death date
		death_year = None


		values = self.return_wikidata_field('P570')
		if len(values)>0:


			if isinstance(values[0]['value']['time'], str) == True: 
				
				values[0]['value']['time'] = values[0]['value']['time'].split('T')[0].replace('+','')
				lifedates_subfields.append('g')
				lifedates_subfields.append(values[0]['value']['time'])

				
				if len(values[0]['value']['time'].split('-')) == 3:
					death_year = values[0]['value']['time'].split('-')[0]


			else:
				self.log('P570 was not a string?',type='warning',msg2=f"{json.dumps(values[0]['value'])}")


		if len(lifedates_subfields) > 0:
			field = Field(
				tag = '046',
				indicators = [' ',' '],
				subfields = lifedates_subfields)
			self.marc_record.add_field(field)




		# build the name 100 now that we have life dates possibly

		
		
		life_dates = None
		if (birth_year != None and death_year != None):
			life_dates = f"{birth_year}-{death_year}"
		elif (birth_year != None and death_year == None):
			life_dates = f"{birth_year}-"
		elif (birth_year == None and death_year != None):
			life_dates = f"-{death_year}"


		# figure out if first indicator should be
		use_100_indicator = '1'

		if re.match(r"^[A-z]+,", use_100):
			use_100_indicator='1'
		elif ',' not in use_100:
			use_100_indicator='0'
		elif re.match(r",\s*\(", use_100):
			use_100_indicator='0'

		print(life_dates)
		if life_dates == None:

			use_100 = str(use_100)
			# if there is life dates in the string split them out
			if re.search(r',\s[0-9]{4}\-[0-9]{4}', use_100):

				m = re.search(r',\s([0-9]{4}\-[0-9]{4})', use_100)

				if m:
					life_dates = m.group(1)

					use_100 = re.sub(r',\s[0-9]{4}\-[0-9]{4}','',use_100)

					self.marc_record.add_field(
						Field(
							tag = '100',
							indicators = [use_100_indicator, ' '],
							subfields = [
							'a', use_100 + ', ',
							'd', life_dates
					]))	


				else:
					self.marc_record.add_field(
						Field(
							tag = '100',
							indicators = [use_100_indicator, ' '],
							subfields = [
							'a', use_100
					]))	

			else:
				self.marc_record.add_field(
					Field(
						tag = '100',
						indicators = [use_100_indicator, ' '],
						subfields = [
						'a', use_100
				]))		
		else:

			# if there are life dates in the 100 strip them out since we have them already

			use_100 = re.sub(r',\s[0-9]{4}\-[0-9]{4}','',use_100)
			use_100 = re.sub(r',\s[0-9]{4}\-','',use_100)


			self.marc_record.add_field(
				Field(
					tag = '100',
					indicators = [use_100_indicator, ' '],
					subfields = [
					'a', use_100+ ', ',
					'd', life_dates
			]))				






	def build_3xx(self):

		self.log_add(f"Building the 3xx fields")

		values = self.return_wikidata_field('P106')

		for v in values:

			qid = v['value']['id']
			wlabel = v['label']
			lccn = v['lccn']
			lccn_label = v['lccn_label']
			lcdgt = v['lcdgt']
			lcdgt_label = v['lcdgt_label']

			# if it has a LCCN use that
			if lcdgt != None and lcdgt_label != None:
				subfields = ['a',lcdgt_label,'2','lcdgt','0',f'http://id.loc.gov/authorities/{lcdgt}']
			elif lccn != None and lccn_label != None:
				subfields = ['a',lccn_label,'2','lcsh','0',f'http://id.loc.gov/authorities/{lccn}']
			else:
				subfields = ['a',wlabel,'2','wikidata','0',f'https://www.wikidata.org/entity/{qid}']

			field = Field(
				tag = '374',
				indicators = [' ',' '],
				subfields = subfields)
			self.marc_record.add_field(field)



		# values = self.return_wikidata_field('P21')

		# for v in values:

		# 	qid = v['value']['id']
		# 	wlabel = v['label']
		# 	lccn = v['lccn']
		# 	lccn_label = v['lccn_label']
		# 	lcdgt = v['lcdgt']
		# 	lcdgt_label = v['lcdgt_label']

		# 	# if it has a LCCN use that
		# 	if lcdgt != None and lcdgt_label != None:
		# 		subfields = ['a',lcdgt_label,'2','lcdgt','0',f'http://id.loc.gov/authorities/{lcdgt}']
		# 	elif lccn != None and lccn_label != None:
		# 		subfields = ['a',lccn_label,'2','lcsh','0',f'http://id.loc.gov/authorities/{lccn}']
		# 	else:
		# 		subfields = ['a',wlabel,'2','wikidata','0',f'https://www.wikidata.org/entity/{qid}']

		# 	field = Field(
		# 		tag = '375',
		# 		indicators = [' ',' '],
		# 		subfields = subfields)
		# 	self.marc_record.add_field(field)



		for p in ['P101','P2650','P812','P811','P452']:


			values = self.return_wikidata_field(p)

			for v in values:

				qid = v['value']['id']
				wlabel = v['label']
				lccn = v['lccn']
				lccn_label = v['lccn_label']
				lcdgt = v['lcdgt']
				lcdgt_label = v['lcdgt_label']

				# if it has a LCCN use that
				if lcdgt != None and lcdgt_label != None:
					subfields = ['a',lcdgt_label,'2','lcdgt','0',f'http://id.loc.gov/authorities/{lcdgt}']
				elif lccn != None and lccn_label != None:
					subfields = ['a',lccn_label,'2','lcsh','0',f'http://id.loc.gov/authorities/{lccn}']
				else:
					subfields = ['a',wlabel,'2','wikidata','0',f'https://www.wikidata.org/entity/{qid}']

				field = Field(
					tag = '372',
					indicators = [' ',' '],
					subfields = subfields)
				self.marc_record.add_field(field)



		for p in ['P1416','P463','P108','P8413','P102','P5096','P54','P749','P355']:

			values = self.return_wikidata_field(p)

			for v in values:

				qid = v['value']['id']
				wlabel = v['label']
				lccn = v['lccn']
				lccn_label = v['lccn_label']
				lcdgt = v['lcdgt']
				lcdgt_label = v['lcdgt_label']

				lccn_type = 'lcsh'
				if lccn != None:
					if 'n' in lccn:
						lccn_type = 'lcnaf'

				# if it has a LCCN use that
				if lcdgt != None and lcdgt_label != None:
					subfields = ['a',lcdgt_label,'2','lcdgt','0',f'http://id.loc.gov/authorities/{lcdgt}']
				elif lccn != None and lccn_label != None:
					subfields = ['a',lccn_label,'2',lccn_type,'0',f'http://id.loc.gov/authorities/{lccn}']
				else:
					subfields = ['a',wlabel,'2','wikidata','0',f'https://www.wikidata.org/entity/{qid}']

				field = Field(
					tag = '373',
					indicators = [' ',' '],
					subfields = subfields)
				self.marc_record.add_field(field)






	def build_4xx(self):


		labels = self.return_wikidata_label(self.qid,all_langs=True)

		# find the en lang label to compare

		en_label = None
		for l in labels:

			if l['lang_code'] == 'en':
				en_label = l['value']


		added_non_latin = False
		for l in labels:

			# only add 400 if tghey are differnt
			if en_label != l['value']:
				added_non_latin=True
				field = Field(
					tag = '400',
					indicators = ['0',' '],
					subfields = [
						'a',l['value']
						# 'l',f"{l['lang']} ({l['lang_code']})"
					])
				self.marc_record.add_field(field)

		if added_non_latin:
			field = Field(
				tag = '667',
				indicators = ['',' '],
				subfields = [
					'a','Non-Latin references not evaluated'
				])
			self.marc_record.add_field(field)

		self.log_add(f"Building the 4xx fields")


	def build_6xx(self):

		self.log_add(f"Building the 6xx fields")



		results = self.return_wikidata_field_reference('P244','P854')


		# print('---P244---P854--')
		# print(results)
		# print('--------')

		if len(results) > 0 and 'value' in results[0]:

			uri = results[0]['value']

			print(uri)
			self.log_add(f"Found a P854 reference to build 670", type="info", msg2=f"URI: {uri}")


			if 'id.loc.gov' in uri:
				uri = uri.lower()
				uri = uri.replace('.html','')
				real_uri = uri
				url = uri + '.bibframe.json'

				check_uris = [ url.replace('.bibframe.json',''), url.replace('.bibframe.json','').replace('https','http')  ]


				r = requests.get(url)
				# print(r.text)
				data = json.loads(r.text)

				titleId = None
				title = None


				for g in data:
					# print('gggggggg',g)
					if g['@id']:
						# print("-----g['@id']",g['@id'])
						if g['@id'] in check_uris:

							for k in g:
								if k == 'http://id.loc.gov/ontologies/bibframe/title':
									if len(g[k]) > 0:
										titleId = g[k][0]['@id']
										# print('----titleId-----',titleId)


				# llook for that id in the graphs


				for g in data:
					if g['@id']:
						if g['@id'] == titleId:

							if g['http://id.loc.gov/ontologies/bibframe/mainTitle']:

								if len(g['http://id.loc.gov/ontologies/bibframe/mainTitle']) > 0:
									if '@value' in g['http://id.loc.gov/ontologies/bibframe/mainTitle'][0]:
										title = g['http://id.loc.gov/ontologies/bibframe/mainTitle'][0]['@value']
										print("----title here-----")
										print(title)



				if title != None:


					viewed_date = datetime.today().strftime('%b. %d, %Y')


					field = Field(
						tag = '670',
						indicators = [' ',' '],
						subfields = [
							'a', f'{title}, viewed {viewed_date}',
							'u', real_uri
					])

					self.marc_record.add_field(field)





			else:

				self.log_add(f"Error not a ID URI", type="error", msg2=f"URI: {uri}")



		# results = self.return_wikidata_field_reference('P244','P248')


		# print('--------')
		# print(results)
		# print('--------')

		# # doing the 670

		# for r in results:


		# 	if r['label'] != None:

		# 		w = f"(wikidata){r['value']['id']}"
		# 		if r['lccn'] != None:
		# 			w = f"(DLC){r['lccn']}"

		# 		field = Field(
		# 			tag = '670',
		# 			indicators = [' ',' '],
		# 			subfields = [
		# 				'a', r['label'],
		# 				'w', w
		# 		])

		# 		self.marc_record.add_field(field)


		# # also add one with just the wiki id and date viewd and name
		# # if we have named_as just use that
		# use_name = None
		# if self.named_as != None:
		# 	use_name = self.named_as
		# else:

		# 	# try to get it
		# 	values = self.return_wikidata_field('P244')
			
		# 	if len(values)>0:
		# 		if values[0]['lccn_label'] != None:
		# 			use_name = values[0]['lccn_label']


		# if use_name == None or use_name == False:

		# 	wiki_label = self.return_wikidata_label(self.qid)

		# 	use_name = wiki_label

		# viewed_date = datetime.today().strftime('%b. %d, %Y')


		# field = Field(
		# 	tag = '670',
		# 	indicators = [' ',' '],
		# 	subfields = [
		# 		'a', f'Wikidata {self.qid}, viewed {viewed_date}',
		# 		'b', use_name
		# ])

		# self.marc_record.add_field(field)





	def build_0xx(self):

		self.log_add(f"Building the 0xx control fields")

		# see if there is a LCCN on this record

		values = self.return_wikidata_field('P244')

		# default to using the qid as the 001
		use_001 = self.qid
		use_003 = None

		if len(values)>0:

			use_001 = values[0]['value']
			use_001 = self.util_lccn_space(use_001)
			use_003 = 'DLC'
			self.log_add(f"Using LCCN '{use_001}' for 001")
		else:
			self.log_add(f"Using Q ID for 001")


		now = datetime.now() # current date and time
		use_005 = now.strftime("%Y%m%d%H%M%S") + '.0'

		# TODO, needs work...
		use_008 = f"{now.strftime('%Y%m%d')}n||acaaaaaan|||||||||||a|ana||||||"

		# field = 

		self.marc_record.add_field(Field(tag='001', data=use_001))
		if use_003 != None:
			self.marc_record.add_field(Field(tag='003', data=use_003))

		self.marc_record.add_field(Field(tag='005', data=use_005))
		self.marc_record.add_field(Field(tag='008', data=use_008))






	def log_add(self, msg,**kwargs):

		log_type = kwargs.get('type', 'info')
		log_stamp = kwargs.get('stamp', time.time())
		log_msg_2 = kwargs.get('msg2', None)


		self.log.append({
			'ts': log_stamp,
			'type': log_type,
			'msg1': msg,
			'msg2': log_msg_2
		})



	def load_item(self):

		if self.named_as != None:




			self.log_add(f"named_as was provided, searching wikidata for '{self.named_as}'")


			search = self.named_as.replace("'","\\'")

			sparql = f"""
				SELECT ?item ?itemLabel
				WHERE
				{{
					?item p:P244 ?statement.
					?statement pq:P1810 '{search}'.
					SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
				}}
			"""

			params = {
				'query' : sparql
			}

			print(sparql)

			try:
				r = requests.get(sparql_endpoint, params=params, headers=headers)
				data = json.loads(r.text)
			except Exception as e:
				self.log_add(f"Could not connect/query wikidata", type="error", msg2=f"Error message: {str(e)}")
				return False


			if 'results' not in data:
				self.log_add(f"Unexpected response from wikidata:",type="error",msg2=f"{data}")
				return False


			if 'bindings' not in data['results']:
				self.log_add(f"Unexpected response from wikidata:",type="error",msg2=f"{data}")
				return False



			if len(data['results']['bindings']) == 0:
				self.log_add(f"Did not find that named_as as a qalifier on P244, will try looking for it as a primary statement",type="warning")		

				sparql = f"""
					SELECT ?item ?itemLabel
					WHERE
					{{
	     				?item p:P1477 '{self.named_as}'.
						SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
					}}
				"""

				params = {
					'query' : sparql
				}

				try:
					r = requests.get(sparql_endpoint, params=params, headers=headers)
					data = json.loads(r.text)
				except Exception as e:
					self.log_add(f"Could not connect/query wikidata",type="error",msg2=f"Error message: {str(e)}")
					return False


				if 'results' not in data:
					self.log_add(f"Unexpected response from wikidata:",type="error",msg2=f"{data}")
					return False


				if 'bindings' not in data['results']:
					self.log_add(f"Unexpected response from wikidata:",type="error",msg2=f"{data}")
					return False


			if len(data['results']['bindings']) == 0:
				self.log_add(f"Did not find that named_as as a qalifier or as a primary statement",type="error")
				return False



			if len(data['results']['bindings']) > 1:
				self.log_add(f"Found more than 1 item using that named_as search, only using the first one.",type="error",msg2=f"{json.dumps(data['results']['bindings'],indent=2)}")


			data = data['results']['bindings'][0]


			self.qid = data['item']['value'].split('/')[-1]
			self.wiki_label = data['itemLabel']['value']


		if self.qid == None:
			self.log_add(f"neither named_as or qid were provided, cannot lookup anything ",type="error")		
			return False


		# try to retrieve the data
		url = f"https://www.wikidata.org/wiki/Special:EntityData/{self.qid}.json"


		try:
			r = requests.get(url, headers=headers)
			if r.status_code != 200:
				self.log_add(f"Asking for json data for {self.qid} recieved status code {r.status_code} cannot continue",type="error")
				return False

		except Exception as e:
			self.log_add(f"Could not connect/query wikidata",type="error",msg2=f"Error message: {str(e)}")
			return False

		try:
			data = json.loads(r.text)
		except Exception as e:
			self.log_add(f"Could not decode response from wikidata",type="error",msg2=f"Response: {r.text}")
			return False

		try:
			self.wiki_record = data['entities'][self.qid]
			cache_wiki[self.qid] = self.wiki_record
		except:
			self.log_add(f"Could not parse the data for this item",type="error",msg2=f"Response: {json.dumps(data,indent=2)}")
			return False





	def init_marc(self):

		self.marc_record = Record()
		self.marc_record.leader[5] = 'n'
		self.marc_record.leader[6] = 'z'
		self.marc_record.leader[9] = 'a'
		self.marc_record.leader[10] = '2'
		self.marc_record.leader[11] = '2'
		self.marc_record.leader[17] = 'n'
		self.marc_record.leader[20] = '4'
		self.marc_record.leader[21] = '5'
		self.marc_record.leader[22] = '0'
		self.marc_record.leader[23] = '0'
		 	
		self.log_add(f"Created MARC Leader")


	def get_full_marc_as_stirng(self):

		tmp = f'{tempfile.gettempdir()}/tmp.mrc'

		print(self.marc_record)
		with open(tmp, 'wb') as out:
			out.write(self.marc_record.as_marc())

		with open(tmp, "rb") as file:
			self.marc_as_base64 = base64.b64encode(file.read())		
			self.marc_as_base64 = self.marc_as_base64.decode('ascii')

		with open(tmp, "rb") as file:
			self.marc_base64_encoded = base64.b64encode(file.read()).decode('utf-8')



		with open(tmp, 'rb') as fh:
			reader = MARCReader(fh)
			for record in reader:
				return str(record)




	def get_full_marc_as_xml(self):

		tmp = f'{tempfile.gettempdir()}/tmp.xml'

		writer = XMLWriter(open(tmp,'wb'))
		writer.write(self.marc_record)
		writer.close()  # Important!

		file = open(tmp,mode='r')
		all_of_it = file.read()
		file.close()

		return all_of_it

