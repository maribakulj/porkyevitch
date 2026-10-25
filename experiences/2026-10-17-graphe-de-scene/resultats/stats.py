import json, random, re, collections
recs=[]
for f in ['train','val','test']:
    recs+=json.load(open(f'raw/{f}.json'))
print('paintings',len(recs))
nobj=[len(r['objects']) for r in recs]
print('objects total',sum(nobj),'paintings with 0 obj',sum(1 for n in nobj if n==0))
nbox=collections.Counter()
for r in recs:
    for k,v in r['objects'].items():
        nbox[len(v['bounding_boxes'])]+=1
print('boxes per entity',sorted(nbox.items())[:10])
items=[]
for r in recs:
    for k,v in r['objects'].items():
        items.append((r['id'],k,v['description'],len(v['bounding_boxes']),[sorted(r['objects'].keys())]))
print('entities',len(items))
random.seed(0)
sample=random.sample(items,300)
json.dump([{'painting_id':a,'entity':b,'description':c,'n_boxes':d,'other_entities_in_painting':e[0]} for a,b,c,d,e in sample],open('sample300.json','w'),ensure_ascii=False,indent=1)
