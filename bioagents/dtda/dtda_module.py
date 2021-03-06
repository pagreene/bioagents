import sys
import logging
from indra.statements import Agent
from kqml import KQMLList, KQMLString
from .dtda import DTDA, DrugNotFoundException, DiseaseNotFoundException
from bioagents import Bioagent
from indra.databases import hgnc_client


logging.basicConfig(format='%(levelname)s: %(name)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger('DTDA')


class DTDA_Module(Bioagent):
    """The DTDA module is a TRIPS module built around the DTDA agent.
    Its role is to receive and decode messages and send responses from and
    to other agents in the system."""
    name = "DTDA"
    tasks = ['IS-DRUG-TARGET', 'FIND-TARGET-DRUG', 'FIND-DRUG-TARGETS',
             'FIND-DISEASE-TARGETS', 'FIND-TREATMENT', 'GET-ALL-DRUGS',
             'GET-ALL-DISEASES', 'GET-ALL-GENE-TARGETS']

    def __init__(self, **kwargs):
        # Instantiate a singleton DTDA agent
        self.dtda = DTDA()
        super(DTDA_Module, self).__init__(**kwargs)

    def respond_is_drug_target(self, content):
        """Response content to is-drug-target request."""
        try:
            drug_arg = content.get('drug')
        except Exception:
            return self.make_failure('INVALID_DRUG')
        try:
            drug = self.get_agent(drug_arg)
        except Exception:
            return self.make_failure('DRUG_NOT_FOUND')
        try:
            target_arg = content.get('target')
            target = self.get_agent(target_arg)
        except Exception:
            return self.make_failure('INVALID_TARGET')
        if is_family(target):
            return self.make_resolve_family_failure(target)

        try:
            is_target = self.dtda.is_nominal_drug_target(drug, target)
        except DrugNotFoundException:
            return self.make_failure('DRUG_NOT_FOUND')
        reply = KQMLList('SUCCESS')
        reply.set('is-target', 'TRUE' if is_target else 'FALSE')
        return reply

    def respond_find_target_drug(self, content):
        """Response content to find-target-drug request."""
        try:
            target_arg = content.get('target')
            target = self.get_agent(target_arg)
        except Exception:
            return self.make_failure('INVALID_TARGET')
        if is_family(target):
            return self.make_resolve_family_failure(target)
        kfilter_agents = content.get('filter_agents')
        filter_agents = Bioagent.get_agent(kfilter_agents) if kfilter_agents \
            else None
        drugs = self.dtda.find_target_drugs(target,
                                            filter_agents=filter_agents)
        reply = KQMLList('SUCCESS')
        reply.set('drugs', Bioagent.make_cljson(drugs))
        return reply

    def respond_find_drug_targets(self, content):
        """Response content to find-drug-target request."""
        try:
            drug_arg = content.get('drug')
            drug = self.get_agent(drug_arg)
        except Exception as e:
            return self.make_failure('INVALID_DRUG')
        kfilter_agents = content.get('filter_agents')
        filter_agents = Bioagent.get_agent(kfilter_agents) if kfilter_agents \
            else None
        logger.info('DTDA looking for targets of %s' % drug.name)
        drug_targets = self.dtda.find_drug_targets(drug,
                                                   filter_agents=filter_agents)

        reply = KQMLList('SUCCESS')
        targets = self.make_cljson(drug_targets)
        reply.set('targets', targets)
        return reply

    @staticmethod
    def _get_agent_from_gene_name(gene_name):
        db_refs = {}
        hgnc_id = hgnc_client.get_hgnc_id(gene_name)
        if hgnc_id:
            db_refs['HGNC'] = hgnc_id
            up_id = hgnc_client.get_uniprot_id(hgnc_id)
            if up_id:
                db_refs['UP'] = up_id
        agent = Agent(gene_name, db_refs=db_refs)
        return agent

    def respond_find_disease_targets(self, content):
        """Response content to find-disease-targets request."""
        try:
            disease_arg = content.get('disease')
            disease = self.get_agent(disease_arg)
        except Exception as e:
            logger.error(e)
            reply = self.make_failure('INVALID_DISEASE')
            return reply

        disease_name = disease.name.lower().replace('-', ' ')
        disease_name = disease_name.replace('cancer', 'carcinoma')
        logger.debug('Disease: %s' % disease_name)

        try:
            res = self.dtda.get_top_mutation(disease_name)
            if res is None:
                return self.make_failure('NO_MUTATION_STATS')
            mut_protein, mut_percent, agents = res

        except DiseaseNotFoundException:
            reply = self.make_failure('DISEASE_NOT_FOUND')
            return reply

        # TODO: get functional effect from actual mutations
        # TODO: add list of actual mutations to response (get from agents)
        # TODO: get fraction not percentage from DTDA (edit get_top_mutation)
        reply = KQMLList('SUCCESS')
        protein = self._get_agent_from_gene_name(mut_protein)
        reply.set('protein', self.make_cljson(protein))
        reply.set('prevalence', '%.2f' % (mut_percent/100.0))
        reply.set('functional-effect', 'ACTIVE')
        return reply

    def respond_find_treatment(self, content):
        """Response content to find-treatment request."""
        try:
            disease_arg = content.get('disease')
            disease = self.get_agent(disease_arg)
        except Exception as e:
            logger.error(e)
            reply = self.make_failure('INVALID_DISEASE')
            return reply

        disease_name = disease.name.lower().replace('-', ' ')
        disease_name = disease_name.replace('cancer', 'carcinoma')
        logger.debug('Disease: %s' % disease_name)

        try:
            res = self.dtda.get_top_mutation(disease_name)
            if res is None:
                return self.make_failure('NO_MUTATION_STATS')
            mut_protein, mut_percent, agents = res
        except DiseaseNotFoundException:
            reply = self.make_failure('DISEASE_NOT_FOUND')
            return reply

        # TODO: get functional effect from actual mutations
        # TODO: add list of actual mutations to response
        # TODO: get fraction not percentage from DTDA
        reply = KQMLList('SUCCESS')
        protein = self._get_agent_from_gene_name(mut_protein)
        reply.set('protein', self.make_cljson(protein))
        reply.set('disease', disease_arg)
        reply.set('prevalence', '%.2f' % (mut_percent/100.0))
        reply.set('functional-effect', 'ACTIVE')
        # These differ only in mutation, which isn't relevant.
        an_agent = agents[0]
        drugs = self.dtda.find_target_drugs(an_agent)
        reply.set('drugs', Bioagent.make_cljson(drugs))
        return reply

    def respond_get_all_drugs(self, content):
        """Respond with all the drugs we have to tell you about."""
        reply = KQMLList('SUCCESS')
        reply.set('drugs', self.make_cljson(self.dtda.get_all_drugs()))
        return reply

    def respond_get_all_diseases(self, content):
        """Respond to the task to list all diseases we handle."""
        reply = KQMLList('SUCCESS')
        reply.set('diseases',
                  KQMLList([KQMLString(disease_name)
                            for disease_name in self.dtda.all_diseases]))
        return reply

    def respond_get_all_gene_targets(self, content):
        reply = KQMLList('SUCCESS')
        reply.set('genes', self.make_cljson(self.dtda.get_all_targets()))
        return reply


def is_family(agent):
    return True if agent.db_refs.get('FPLX') else False


if __name__ == "__main__":
    DTDA_Module(argv=sys.argv[1:])
