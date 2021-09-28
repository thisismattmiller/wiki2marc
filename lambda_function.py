import json
from wiki2marc import Wiki2MARC

def lambda_handler(event, context):

    request_data = event['queryStringParameters']

    if 'named_as' in request_data:
        record = Wiki2MARC(named_as=request_data['named_as'])
    elif 'qid' in request_data:
        record = Wiki2MARC(qid=request_data['qid'])
    else:
        return {
            'statusCode': 500,
            'body': json.dumps('No QID or named_as provided')
        }



    record.load_item()
    record.init_marc()
    record.build_0xx()
    record.build_1xx()
    record.build_3xx()
    record.build_4xx()
    record.build_6xx()

    marc_string = record.get_full_marc_as_stirng()
    marc_xml_string = record.get_full_marc_as_xml()

    results = {
        'log': record.log,
        'base64': record.marc_as_base64,
        'string': marc_string,
        'xml': marc_xml_string
    }

    if 'format' in request_data:
        if request_data['format'] == 'xml':


            return {
                'statusCode': 200,
                'headers': {
                    "Content-Type": "text/xml",
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': marc_xml_string
            }

        if request_data['format'] == 'mrc' or request_data['format'] == 'marc':

            
            return {
                'statusCode': 200,
                'isBase64Encoded' : True,
                'headers': {
                    "Content-Type": "application/marc",
                    "content-encoding": "base64",
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
                    'Content-Disposition': 'attachment; filename=' + record.qid + '.mrc'
                },
                'body': record.marc_base64_encoded
            }




    else:


        return {
            'statusCode': 200,
            'headers': {
                "Content-Type": "application/json",
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps(results)
        }

