import connexion

import anchore_engine.clients.catalog
import anchore_engine.services.common
import anchore_engine.configuration.localconfig
import anchore_engine.subsys.servicestatus
from anchore_engine.subsys import logger

def status():
    httpcode = 500
    try:
        localconfig = anchore_engine.configuration.localconfig.get_config()
        return_object = anchore_engine.subsys.servicestatus.get_status({'hostid': localconfig['host_id'], 'servicename': 'analyzer'})
        #return_object = {
        #    'busy':False,
        #    'up':True,
        #    'message': 'all good'
        #}
        httpcode = 200
    except Exception as err:
        return_object = str(err)

    return(return_object, httpcode)

def interactive_analyze(bodycontent):

    try:
        return_object = {}
        httpcode = 500

        request_inputs = anchore_engine.services.common.do_request_prep(connexion.request, default_params={})

        user_auth = request_inputs['auth']
        method = request_inputs['method']
        #bodycontent = request_inputs['bodycontent']
        params = request_inputs['params']
        userId = request_inputs['userId']

        try:
            #input prep
            #jsondata = json.loads(bodycontent)
            jsondata = bodycontent
            tag = jsondata.pop('tag', None)
            if not tag:
                httpcode = 500
                raise Exception("must supply a valid tag param in json body")

            try:
                # image prep
                registry_creds = anchore_engine.clients.catalog.get_registry(user_auth)
                image_info = anchore_engine.services.common.get_image_info(userId, "docker", tag, registry_lookup=True, registry_creds=registry_creds)
                pullstring = image_info['registry'] + "/" + image_info['repo'] + "@" + image_info['digest']
                fulltag = image_info['registry'] + "/" + image_info['repo'] + ":" + image_info['tag']            
                new_image_record = anchore_engine.services.common.make_image_record(userId, 'docker', fulltag, registry_lookup=False, registry_creds=(None, None))
                image_detail = new_image_record['image_detail'][0]
                if not image_detail:
                    raise Exception("no image found matching input")

            except Exception as err:
                httpcode = 404
                raise Exception(str(err))

            image_data, query_data = anchore_engine.services.analyzer.perform_analyze(userId, pullstring, fulltag, image_detail, registry_creds)
            if image_data:
                return_object = image_data
                httpcode = 200
            else:
                httpcode = 500
                raise Exception("analyze resulted in empty analysis data")
        except Exception as err:
            logger.error(str(err))
            raise err
    except Exception as err:
        logger.error(str(err))
        return_object = str(err)

    return(return_object, httpcode)
    #return(json.dumps(return_object, indent=4)+"\n", httpcode)
