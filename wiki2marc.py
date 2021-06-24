import requests
import pymarc
import json
import time
from pymarc import Record, Field, MARCReader, XMLWriter
from datetime import datetime
import tempfile
import base64


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


	def return_wikidata_label(self,qid):

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

		self.named_as = None

		# if we have named_as just use that
		use_100 = None
		if self.named_as != None:
			use_100 = self.named_as
		else:

			# try to get it
			values = self.return_wikidata_field('P244')
			
			if len(values)>0:
				if values[0]['lccn_label'] != None:
					use_100 = values[0]['lccn_label']


		if use_100 == None:

			wiki_label = self.return_wikidata_label(self.qid)

			use_100 = wiki_label + ' - NOT DIRECT ORDER -'


		self.marc_record.add_field(
			Field(
				tag = '100',
				indicators = ['0', ' '],
				subfields = [
				'a', use_100
		]))



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

		values = self.return_wikidata_field('P569')
		if len(values)>0:


			if isinstance(values[0]['value']['time'], str) == True: 
				
				values[0]['value']['time'] = values[0]['value']['time'].split('T')[0].replace('+','')
					
				lifedates_subfields.append('f')
				lifedates_subfields.append(values[0]['value']['time'])


			else:
				self.log('P569 was not a string?',type='warning',msg2=f"{json.dumps(values[0]['value'])}")


		# death date
		values = self.return_wikidata_field('P570')
		if len(values)>0:


			if isinstance(values[0]['value']['time'], str) == True: 
				
				values[0]['value']['time'] = values[0]['value']['time'].split('T')[0].replace('+','')
				lifedates_subfields.append('g')
				lifedates_subfields.append(values[0]['value']['time'])

			else:
				self.log('P570 was not a string?',type='warning',msg2=f"{json.dumps(values[0]['value'])}")


		if len(lifedates_subfields) > 0:
			field = Field(
				tag = '046',
				indicators = [' ',' '],
				subfields = lifedates_subfields)
			self.marc_record.add_field(field)


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



		values = self.return_wikidata_field('P21')

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
				tag = '375',
				indicators = [' ',' '],
				subfields = subfields)
			self.marc_record.add_field(field)



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



	def build_6xx(self):

		self.log_add(f"Building the 6xx fields")

		results = self.return_wikidata_field_reference('P244','P248')

		# doing the 670

		for r in results:
			if r['label'] != None:

				w = f"(wikidata){r['value']['id']}"
				if r['lccn'] != None:
					w = f"(DLC){r['lccn']}"

				field = Field(
					tag = '670',
					indicators = [' ',' '],
					subfields = [
						'a', r['label'],
						'w', w
				])

				self.marc_record.add_field(field)





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

