

def convert_sparql_result(inp, config):
    res = dict()
    for k, v in config.items():
        if v == 'id':
            anchor = k
    for it in inp['results']['bindings']:
        c_uri = it[anchor]['value']
        if c_uri not in res:
            res[c_uri] = dict()
        del per[anchor]
        for k, v in per.items():
            if k in res[c_uri]:
                res[c_uri][k].append(v['value'])
            else:
                res[c_uri][k] = [v['value']]
    return res