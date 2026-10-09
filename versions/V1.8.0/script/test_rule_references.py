import unittest
import io
import test_retailer_setup as fixtures
from retailer_setup import REFERENCE_RULES, BUILTINS, apply_pipeline, validate_pipeline


class ReferenceCatalogTests(unittest.TestCase):
    def test_complete_catalog_and_short_examples(self):
        self.assertEqual(len(REFERENCE_RULES), 496)
        self.assertEqual({r['category'] for r in REFERENCE_RULES}, {'Cleaning', 'Transformation', 'Validation'})
        for entry in REFERENCE_RULES + BUILTINS:
            self.assertGreater(len(entry['example'].split()), 0)
            self.assertLess(len(entry['example'].split()), 10, entry['name'])
            self.assertNotIn('Example:', entry['name'])

    def test_reference_execution_rejected_but_configuration_allowed(self):
        entry = next(r for r in REFERENCE_RULES if r['operation'] == 'reference')
        pipeline = [{**entry, 'description': 'My reason for this rule'}]
        validate_pipeline(pipeline, allow_references=True)
        with self.assertRaisesRegex(ValueError, 'execution engine is not available'):
            apply_pipeline([{'sku': ' a '}], pipeline)

    def test_mapped_trim_executes(self):
        entry = next(r for r in REFERENCE_RULES if r['name'] == 'Trim leading and trailing spaces')
        result, _, _, _ = apply_pipeline([{'sku': ' a '}], [{**entry, 'field': 'sku'}])
        self.assertEqual(result[0]['sku'], 'a')


class ReferenceApiTests(unittest.TestCase):
    setUp = fixtures.RetailerSetupTests.setUp
    # Reuse retailer setup without duplicating its test suite.
    def test_catalog_api_contains_every_reference(self):
        entries = self.client.get('/api/v1/rule-definitions').get_json()['rules']
        available = {(r['category'], r['name']) for r in entries}
        self.assertTrue(all((r['category'], r['name']) in available for r in REFERENCE_RULES))

    def test_reference_configuration_persists(self):
        entry = next(r for r in REFERENCE_RULES if r['operation'] == 'reference')
        pipeline = [{**entry, 'description': 'Check retailer source consistency'}]
        response = self.client.put(f'/api/v1/retailers/{self.rid}', json={**self.body, 'pipeline': pipeline})
        self.assertEqual(response.status_code, 200, response.data)
        restored = next(r for r in self.client.get('/api/v1/retailers').get_json()['retailers'] if r['id'] == self.rid)
        self.assertEqual(restored['pipeline'], pipeline)

    def test_reference_preview_and_export_return_clear_error(self):
        self.client.post(f'/api/v1/retailers/{self.rid}/sample', data={'file': (io.BytesIO(b'sku\na\n'), 'sample.csv')})
        entry = next(r for r in REFERENCE_RULES if r['operation'] == 'reference')
        for endpoint in ['preview', 'example.csv']:
            response = self.client.post(f'/api/v1/retailers/{self.rid}/{endpoint}', json={'pipeline': [entry]})
            self.assertEqual(response.status_code, 400)
            self.assertIn('execution engine is not available', response.get_data(as_text=True))
