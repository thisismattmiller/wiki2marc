from wiki2marc import Wiki2MARC
import json


# record = Wiki2MARC(named_as='Clarke, Arthur C. (Arthur Charles), 1917-2008')
record = Wiki2MARC(qid='Q40909')


# record = Wiki2MARC(named_as="D'Aurelio, D. A.")





record.load_item()
record.init_marc()
record.build_0xx()
record.build_1xx()
record.build_3xx()
record.build_6xx()

marc_string = record.get_full_marc_as_stirng()

print(marc_string)


marc_xml_string = record.get_full_marc_as_xml()

print(marc_xml_string)


results = {
	'log': record.log,
	'base64': record.marc_as_base64,
	'string': marc_string,
	'xml': marc_xml_string
}

print(json.dumps(results,indent=2))

print(record.marc_base64_encoded)


# print(record.marc_record)


# for x in record.log:
# 	print(x)



# results = wiki2marc.init_marc(results)

# results = wiki2marc.build_xx0(results)