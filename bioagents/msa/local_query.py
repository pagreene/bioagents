import pickle
import requests
from collections import defaultdict
from indra.statements import *
from indra.assemblers.html.assembler import get_available_source_counts, \
    _get_available_ev_source_counts


def load_from_config(config_str):
    config_type, config_val = config_str.split(':', maxsplit=1)
    if config_type == 'emmaa':
        model_name = config_val
        url = ('https://emmaa.s3.amazonaws.com/assembled/%s/'
            'latest_statements_%s.json' % (model_name, model_name))
        res = requests.get(url)
        stmts = stmts_from_json(res.json())
        return LocalQueryProcessor(stmts)
    elif config_type == 'pickle':
        with open(config_val, 'rb') as fh:
            stmts = pickle.load(fh)
            return LocalQueryProcessor(stmts)
    else:
        raise ValueError('Invalid config_str: %s' % config_str)


class LocalQueryProcessor:
    def __init__(self, all_stmts):
        self.all_stmts = all_stmts
        self._stmts_lookup = self._build_lookups()
        self.statements = []

    def get_statements(self, subject=None, object=None, agents=None,
                       stmt_type=None,
                       use_exact_type=False, persist=True,
                       simple_response=False,
                       *api_args, **api_kwargs):
        if subject:
            subj_stmts = self._get_stmts_by_key_role(
                self._tuple_from_at_key(subject), 'SUBJ')
            all_stmts = subj_stmts

        if object:
            obj_stmts = self._get_stmts_by_key_role(
                self._tuple_from_at_key(object), 'OBJ')
            all_stmts = obj_stmts

        if subject and object:
            all_stmts = self._get_intersection(subj_stmts, obj_stmts)

        if agents:
            ag1_stmts = self._get_stmts_by_key_role(
                self._tuple_from_at_key(agents[0]), None)
            if len(agents) > 1:
                ag2_stmts = self._get_stmts_by_key_role(
                    self._tuple_from_at_key(agents[1]), None)
                all_stmts = self._get_intersection(ag1_stmts, ag2_stmts)
            else:
                all_stmts = ag1_stmts

        stmts = self._filter_for_type(all_stmts, stmt_type)
        self.statements = stmts
        return self

    def _filter_for_type(self, stmts, verb):
        from .msa import verb_map
        if verb is None or verb.lower() == 'unknown':
            return stmts
        mapped_verb = verb_map.get(verb)
        if not mapped_verb:
            return stmts
        return [s for s in stmts if s.__class__.__name__ == mapped_verb]

    def _get_stmts_by_key_role(self, key, role):
        stmts = self._stmts_lookup.get(key)
        if not stmts:
            return []
        return [s for s, r in stmts if role is None or r == role]

    def _get_intersection(self, stmts1, stmts2):
        sh1 = {stmt.get_hash(): stmt for stmt in stmts1}
        sh2 = {stmt.get_hash(): stmt for stmt in stmts2}
        match = set(sh1.keys()) & set(sh2.keys())
        return [s for k, s in sh1.items() if k in match]

    def _tuple_from_at_key(self, at_key):
        db_id, db_ns = at_key.split('@')
        return db_ns, db_id

    def _build_lookups(self):
        stmts_lookup = defaultdict(list)
        for stmt in self.all_stmts:
            agents = stmt.agent_list()
            for idx, agent in enumerate(agents):
                if agent is None:
                    continue
                role = self._get_agent_role(stmt, idx)
                keys = self._get_agent_keys(agent)
                for key in keys:
                    stmts_lookup[key].append((stmt, role))
        return stmts_lookup

    def _get_agent_role(self, stmt, idx):
        if isinstance(stmt, (RegulateAmount, RegulateActivity,
                             Modification, Conversion, Gap, Gef)):
            return 'SUBJ' if idx == 0 else 'OBJ'
        elif isinstance(stmt, (Complex, ActiveForm, Translocation,
                               SelfModification)):
            return 'SUBJ'
        else:
            assert False, stmt

    def _get_agent_keys(self, agent):
        db_ns, db_id = agent.get_grounding()
        if db_ns and db_id:
            return [(db_ns, db_id), ('NAME', agent.name),
                    # TODO: this could be replaced by actual text
                    ('TEXT', agent.name)]
        else:
            keys = []
            if 'TEXT' in agent.db_refs:
                keys.append(('TEXT', agent.db_refs['TEXT']))
            keys.append(('NAME', agent.name))
            return keys

    def get_source_counts(self):
        return get_available_source_counts(self.statements)

    def get_source_count(self, stmt):
        return _get_available_ev_source_counts(stmt.evidence)

    def get_ev_count(self, stmt):
        return len(stmt.evidence)

    def get_ev_counts(self):
        return {s.get_hash(): len(s.evidence) for s in self.statements}

    def wait_until_done(self, timeout=None):
        return

    def is_working(self):
        return False

    def merge_results(self, np):
        self.statements += np.statements

