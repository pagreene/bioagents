import json
from kqml import KQMLList
from indra.statements import *
from util import ekb_from_text
from bioagents.mra import MRA, MRA_Module
from bioagents.mra.mra_module import ekb_from_agent, get_target


def test_agent_to_ekb():
    egfr = Agent('EGFR', db_refs = {'HGNC': '3236', 'TEXT': 'EGFR'})
    term = ekb_from_agent(egfr)
    egfr_out = get_target(term)
    assert(isinstance(egfr_out, Agent))
    assert(egfr_out.name == 'EGFR')


def test_build_model_from_ekb():
    m = MRA()
    ekb = ekb_from_text('MAP2K1 phosphorylates MAPK1.')
    res = m.build_model_from_ekb(ekb)
    assert(res.get('model'))
    assert(res.get('model_id') == 1)
    assert(res.get('model_exec'))
    assert(len(m.models[1]) == 1)
    assert(isinstance(m.models[1][0], Phosphorylation))
    assert(m.models[1][0].enz.name == 'MAP2K1')


def test_expand_model_from_ekb():
    m = MRA()
    ekb = ekb_from_text('MAP2K1 phosphorylates MAPK1.')
    res = m.build_model_from_ekb(ekb)
    model_id = res.get('model_id')
    assert(res.get('model'))
    assert(res.get('model_id') == 1)
    assert(len(m.models[1]) == 1)
    ekb = ekb_from_text('MAP2K2 phosphorylates MAPK1.')
    res = m.expand_model_from_ekb(ekb, model_id)
    assert(res.get('model'))
    assert(res.get('model_id') == 2)
    assert(len(m.models[2]) == 2)


def test_respond_build_model_from_json():
    mm = MRA_Module(testing=True)
    st = Phosphorylation(Agent('MEK'), Agent('ERK'))
    msg = KQMLList('BUILD-MODEL')
    msg.sets('description', json.dumps(stmts_to_json([st])))
    msg.sets('format', 'indra_json')
    reply = mm.respond_build_model(msg)
    assert(reply.get('model'))
    assert(reply.get('model-id') == '1')


def test_respond_expand_model_from_json():
    mm = MRA_Module(testing=True)
    st = Phosphorylation(Agent('MEK'), Agent('ERK'))
    msg = KQMLList('BUILD-MODEL')
    msg.sets('description', json.dumps(stmts_to_json([st])))
    msg.sets('format', 'indra_json')
    reply = mm.respond_build_model(msg)
    assert(reply.get('model'))
    assert(reply.get('model-id') == '1')
    st = Phosphorylation(Agent('RAF'), Agent('MEK'))
    msg = KQMLList('EXPAND-MODEL')
    msg.sets('description', json.dumps(stmts_to_json([st])))
    msg.sets('format', 'indra_json')
    msg.set('model-id', '1')
    reply = mm.respond_expand_model(msg)
    assert(reply.get('model'))
    assert(reply.get('model-id') == '2')


def test_get_upstream():
    m = MRA()
    egfr = Agent('EGFR', db_refs = {'HGNC': '3236', 'TEXT': 'EGFR'})
    kras = Agent('KRAS', db_refs = {'HGNC': '6407', 'TEXT': 'KRAS'})
    stmts = [Activation(egfr, kras)]
    model_id = m.new_model(stmts)
    upstream = m.get_upstream(kras, model_id)
    assert(len(upstream) == 1)
    assert(upstream[0].name == 'EGFR')


def test_respond_model_get_upstream():
    mm = MRA_Module(testing=True)
    egfr = Agent('EGFR', db_refs = {'HGNC': '3236', 'TEXT': 'EGFR'})
    kras = Agent('KRAS', db_refs = {'HGNC': '6407', 'TEXT': 'KRAS'})
    stmts = [Activation(egfr, kras)]
    model_id = mm.mra.new_model(stmts)
    kras_term = ekb_from_agent(kras)
    msg = KQMLList('MODEL-GET-UPSTREAM')
    msg.sets('target', kras_term)
    msg.set('model-id', str(model_id))
    reply = mm.respond_model_get_upstream(msg)
    ups = reply.get('upstream')
    assert(len(ups) == 1)


def test_undo():
    mm = MRA_Module(testing=True)
    kl = KQMLList.from_string('(BUILD-MODEL :DESCRIPTION "<ekb><EVENT id=\\"V34357\\"><type>ONT::ACTIVATE</type><arg1 id=\\"V34353\\" role=\\":AGENT\\" /><arg2 id=\\"V34364\\" role=\\":AFFECTED\\" /></EVENT><TERM id=\\"V34364\\" dbid=\\"FA:03114|BE:RAF|NCIT:C51274|UP:Q06891\\"><features></features><type>ONT::GENE-PROTEIN</type><name>RAF</name><drum-terms><drum-term dbid=\\"FA:03114\\" match-score=\\"1.0\\" name=\\"RAF subfamily\\" /><drum-term dbid=\\"BE:RAF\\" match-score=\\"1.0\\" name=\\"RAF\\" /><drum-term dbid=\\"NCIT:C51274\\" match-score=\\"0.82857\\" name=\\"RAF1\\" /><drum-term dbid=\\"UP:Q06891\\" match-score=\\"0.65714\\" name=\\"Trans-acting factor D\\" /></drum-terms></TERM><TERM id=\\"V34353\\" dbid=\\"NCIT:C52545|HGNC:5173|NCIT:C16659|NCIT:C17382\\"><features></features><type>ONT::GENE-PROTEIN</type><name>HRAS</name><drum-terms><drum-term dbid=\\"NCIT:C52545\\" match-score=\\"1.0\\" name=\\"HRAS\\" /><drum-term dbid=\\"HGNC:5173\\" match-score=\\"1.0\\" name=\\"Harvey rat sarcoma viral oncogene homolog\\" /><drum-term dbid=\\"NCIT:C16659\\" match-score=\\"0.82857\\" name=\\"oncogene H-ras\\" /><drum-term dbid=\\"NCIT:C17382\\" match-score=\\"0.82857\\" name=\\"p21 H-ras protein\\" /></drum-terms></TERM></ekb>")')
    reply = mm.respond_build_model(kl)
    print(reply)
    kl = KQMLList.from_string('(EXPAND-MODEL :MODEL-ID 1 :DESCRIPTION "<ekb><EVENT id=\\"V34455\\"><type>ONT::ACTIVATE</type><arg1 id=\\"V34451\\" role=\\":AGENT\\" /><arg2 id=\\"V34462\\" role=\\":AFFECTED\\" /></EVENT><TERM id=\\"V34462\\" dbid=\\"FA:03114|BE:RAF|NCIT:C51274|UP:Q06891\\"><features></features><type>ONT::GENE-PROTEIN</type><name>RAF</name><drum-terms><drum-term dbid=\\"FA:03114\\" match-score=\\"1.0\\" name=\\"RAF subfamily\\" /><drum-term dbid=\\"BE:RAF\\" match-score=\\"1.0\\" name=\\"RAF\\" /><drum-term dbid=\\"NCIT:C51274\\" match-score=\\"0.82857\\" name=\\"RAF1\\" /><drum-term dbid=\\"UP:Q06891\\" match-score=\\"0.65714\\" name=\\"Trans-acting factor D\\" /></drum-terms></TERM><TERM id=\\"V34451\\" dbid=\\"NCIT:C52549|HGNC:7989|NCIT:C16889|NCIT:C17384\\"><features></features><type>ONT::GENE-PROTEIN</type><name>NRAS</name><drum-terms><drum-term dbid=\\"NCIT:C52549\\" match-score=\\"1.0\\" name=\\"NRAS\\" /><drum-term dbid=\\"HGNC:7989\\" match-score=\\"1.0\\" name=\\"neuroblastoma RAS viral oncogene homolog\\" /><drum-term dbid=\\"NCIT:C16889\\" match-score=\\"0.82857\\" name=\\"oncogene N-RAS\\" /><drum-term dbid=\\"NCIT:C17384\\" match-score=\\"0.82857\\" name=\\"p21 N-ras protein\\" /></drum-terms></TERM></ekb>")')
    reply = mm.respond_expand_model(kl)
    print(reply)
    kl = KQMLList.from_string('(MODEL-UNDO)')
    reply = mm.respond_model_undo(kl)
    print(reply)

def test_has_mechanism():
    m = MRA()
    ekb = ekb_from_text('BRAF binds MEK')
    m.build_model_from_ekb(ekb)
    has_mechanism = m.has_mechanism(ekb, 1)
    assert(has_mechanism)

'''
def test_replace_agent_one():
    m = MRA()
    m.build_model_from_text('BRAF binds MEK1.')
    m.replace_agent('BRAF', ['RAF1'], 1)
    assert(len(m.statements) == 1)
    assert(len(m.statements[0]) == 1)
    assert((m.statements[0][0].members[0].name == 'RAF1') or\
            (m.statements[0][0].members[1].name == 'RAF1'))


def test_find_family_members_name():
    m = MRA()
    family_members = m.find_family_members('Raf')
    assert(family_members is not None)
    assert(len(family_members) == 3)
    assert('BRAF' in family_members)

def test_find_family_members_id():
    m = MRA()
    family_members = m.find_family_members('', family_id='FA:03114')
    assert(family_members is not None)
    assert(len(family_members) == 3)
    assert('BRAF' in family_members)
'''
