import dataiku

CLIENT = dataiku.api_client()

def do(payload, config, plugin_config, inputs):
    choices = []
    clusters = CLIENT.list_clusters()
    
    for cluster in clusters:
        print(cluster)
        if cluster['architecture'] == 'KUBERNETES':
            choices.append({'value': cluster['name'], 'label': cluster['name']})
            
    return {'choices': choices}