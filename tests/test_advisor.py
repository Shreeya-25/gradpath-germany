import sys, unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from advisor import tools as T
from advisor.agent import Advisor
from advisor.ingest import load_chunks
from advisor.retrieval import HybridRetriever
from advisor.textutil import split_sentences


class TestIngest(unittest.TestCase):
    def test_chunks_have_metadata(self):
        chunks = load_chunks()
        self.assertGreater(len(chunks), 25)
        for c in chunks:
            self.assertTrue(c.doc_id and c.university and c.source_type and c.section)

    def test_sentence_splitter_keeps_abbreviations(self):
        s = split_sentences("It needs a B.Sc. degree, e.g. in CS. Second sentence here.")
        self.assertEqual(len(s), 2)


class TestTools(unittest.TestCase):
    def test_cgpa_conversion_range(self):
        r = T.convert_cgpa_to_german(8.4, 10)
        self.assertAlmostEqual(r["estimate_low"], 1.8, places=2)
        self.assertAlmostEqual(r["estimate_high"], 2.17, places=1)

    def test_borderline_grade_flagged_as_risk(self):
        rep = T.check_eligibility(T.Profile(cgpa=8.4), "tuebingen_ml")
        grade = next(c for c in rep.checks if c.name == "Minimum grade")
        self.assertEqual(grade.status, "risk")

    def test_low_grade_fails(self):
        rep = T.check_eligibility(T.Profile(cgpa=6.5), "tuebingen_ml")
        grade = next(c for c in rep.checks if c.name == "Minimum grade")
        self.assertEqual(grade.status, "fail")
        self.assertIn("Does not meet", rep.verdict)

    def test_tum_gre_requirement(self):
        todo = T.check_eligibility(T.Profile(), "tum_informatics")
        self.assertEqual(next(c for c in todo.checks if c.name == "GRE/GATE").status, "todo")
        ok = T.check_eligibility(T.Profile(gre_quant=165, gre_awa=4.0), "tum_informatics")
        self.assertEqual(next(c for c in ok.checks if c.name == "GRE/GATE").status, "pass")
        low = T.check_eligibility(T.Profile(gre_quant=160, gre_awa=4.0), "tum_informatics")
        self.assertEqual(next(c for c in low.checks if c.name == "GRE/GATE").status, "fail")

    def test_tum_degree_name_is_risk_for_aiml(self):
        rep = T.check_eligibility(T.Profile(), "tum_informatics")
        self.assertEqual(next(c for c in rep.checks if c.name == "Degree field").status, "risk")

    def test_deadlines(self):
        d = T.get_deadlines("tum_informatics", "winter", 2027, today=date(2026, 10, 14))
        self.assertEqual(d["deadline"], "2027-05-31")
        self.assertEqual(d["recommended_for_visa_applicants"], "2027-03-31")
        self.assertEqual(d["days_left"], 229)
        s = T.get_deadlines("saarland_dsai", "winter", 2027, today=date(2026, 10, 14))
        self.assertEqual(s["confidence"], "low")  # sources disagree

    def test_find_program(self):
        self.assertEqual(T.find_program("tuebingen machine learning deadline"), ["tuebingen_ml"])
        self.assertIn("tum_informatics", T.find_program("TUM Informatics GRE"))
        self.assertEqual(T.find_program("what is the weather"), [])


class TestRetrievalAndAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adv = Advisor()

    def test_superseded_page_is_demoted(self):
        hits = self.adv.retriever.search("minimum german grade tuebingen machine learning", k=3,
                                         program_hint="MSc Machine Learning", university_hint="University of Tuebingen")
        self.assertEqual(hits[0].chunk.doc_id, "tuebingen_ml_requirements_2026")

    def test_asking_for_old_version_surfaces_it(self):
        hits = self.adv.retriever.search("what grade threshold did the older tuebingen page use", k=3)
        self.assertEqual(hits[0].chunk.doc_id, "tuebingen_ml_requirements_2025_cached")

    def test_agent_routes_deadline_intent(self):
        res = self.adv.run("What is the TUM Informatics winter deadline?", today=date(2026, 10, 14))
        self.assertIn("deadline", res.intents)
        self.assertIn("2027-05-31", res.answer)
        self.assertIn("get_deadlines", [c["tool"] for c in res.tool_calls])

    def test_agent_eligibility_uses_profile(self):
        res = self.adv.run("Am I eligible for the Tuebingen machine learning master?", T.Profile(cgpa=8.4))
        self.assertIn("borderline", res.answer)

    def test_agent_declines_out_of_scope(self):
        res = self.adv.run("What is the weather in Berlin today?")
        self.assertIn("could not find", res.answer)

    def test_answers_carry_citations(self):
        res = self.adv.run("What GRE score do I need for TUM Informatics?")
        self.assertIn("164", res.answer)
        self.assertIn("[1]", res.answer)
        self.assertIn("https://www.cit.tum.de", res.sources)


if __name__ == "__main__":
    unittest.main()
