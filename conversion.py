from SPARQLTransformer import post_process


def convert_sparql_result(inp, config, opt):
    res = post_process(inp, config, opt)

    return res
# def convert_layer(inp, res, config):
#     for k, v in config:
#         if v.endswith('$anchor'):
#             anchor = k
#     for it in inp:
#         c_uri = it[anchor]
#         if c_uri not in res:
#             res[c_uri] = dict()
#         del it[anchor]
#         for k, v in it.items():
#             if k in res[c_uri]:
#                 res[c_uri][k].append(v)
#             else:
#                 res[c_uri][k] = [v]

# def convert_sparql_result(inp, config):
#     res = []
#     layers = []
#     for k, v in config.items():
#         layers.append((k, v))
#     current_layer = [] 
#     next_level = []
#     while len(current_layer) > 0:
#         current_layer = []
#         for k, v in next_level:
#             if isinstance(v, str):
#                 current_layer.append((k, v))
#             else:
#                 next_level.append((f"{k}.${type(k).__name__}", v))
#         res = convert_layer(inp, res, current_layer)

# def convert_sparql_result_bak(inp, config):
#     res = dict()
#     for k, v in config.items():
#         if v == 'id':
#             anchor = k
#     for it in inp['results']['bindings']:
#         c_uri = it[anchor]['value']
#         if c_uri not in res:
#             res[c_uri] = dict()
#         del it[anchor]
#         for k, v in per.items():
#             if k in res[c_uri]:
#                 res[c_uri][k].append(v['value'])
#             else:
#                 res[c_uri][k] = [v['value']]
#     return res
