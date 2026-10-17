import json
import unittest
import importlib.util
from io import BytesIO

from src.cqbal_import import parse_report_text, parse_pdf, convert_report, provenance_json
from src.config import NUTRIENT_BY_CODE


def report_text(body):
    return ('CQBAL 4.0\nCONCENTRADOS PROTEICOS\nALGODÃO\nGossypium hirsutum\n'
            'ALGODÃO CAROÇO\nDerivados\nNUTRIENTE MÉDIA N S NUTRIENTE MÉDIA N S\n'
            + body + '\nNutrientes Calculados\nNDT_BRCORTE2016 96.35 1 -\n')


class ImportTests(unittest.TestCase):
    def test_exact_codes_and_missing(self):
        report = parse_report_text(report_text('MS 90.66 64 1.353 PB 22.94 60 1.183\n'
            'NDT OBS 81.46 10 2.297 NDT(iv) 63.50 1 -\n'
            'FDN 45.65 41 1.709 FDNcp 41.70 10 1.735\n'
            'FDA 33.81 31 1.829 FDAp 34.40 1 -\n'
            'EE 20.06 52 1.266 MM 4.28 38 0.838\nFB 25.39 10 1.481 AMIDO 0.65 2 0.837'))
        values, preview, missing = convert_report(report, '%')
        self.assertEqual(values['NDT'], 81.46)
        self.assertEqual(values['FDN'], 45.65)
        self.assertEqual(values['FDA'], 33.81)
        self.assertEqual(values['EE'], 20.06)
        self.assertEqual(values['MM'], 4.28)
        self.assertEqual(values['FB'], 25.39)
        self.assertIsNone(values['Se'])
        self.assertIn('Se', missing)
        self.assertEqual(len(preview), len(report.records))

    def test_units(self):
        report = parse_report_text(report_text('Ca 12 2 1.2 P 0 1 -\nZn 50 2 0.1 Se 0.1 1 -'))
        v, _, _ = convert_report(report, 'g/kg')
        self.assertEqual(v['CA'], 1.2)
        self.assertEqual(v['P'], 0)
        self.assertEqual(v['Zn'], 0.005)
        self.assertEqual(v['Se'], 0.00001)
        self.assertEqual(convert_report(report, '%')[0]['CA'], 12)
        self.assertTrue(all(NUTRIENT_BY_CODE[c].unit == '%' for c in ['Zn','Se','EE','MM','FB']))

    def test_no_ndt_fallback(self):
        report = parse_report_text(report_text('MS 90 1 - NDT(iv) 60 1 -'))
        self.assertIsNone(convert_report(report, '%')[0]['NDT'])

    def test_provenance(self):
        report = parse_report_text(report_text('MS 90 10 1.2'), 'abc')
        source = json.loads(provenance_json(report, '%', 'fonte.pdf'))
        self.assertEqual(source['registros'][0]['n'], 10)
        self.assertEqual(source['registros'][0]['s'], 1.2)
        self.assertEqual(source['sha256'], 'abc')

    def test_reject_bad_input(self):
        for text in ['', report_text('MS 90 1 -').replace('Nutrientes Calculados',''),
                     report_text('MS 90 1 -\nMS 80 1 -'),
                     report_text('MS 90 1 -')+'\nOUTRO ALIMENTO\nDerivados']:
            with self.assertRaises(ValueError):
                parse_report_text(text)
        with self.assertRaises(ValueError):
            parse_pdf(b'invalid')
        with self.assertRaises(ValueError):
            convert_report(parse_report_text(report_text('MS 90 1 -')), 'indefinida')

    def test_digital_pdf(self):
        from reportlab.pdfgen import canvas
        pdf = BytesIO()
        page = canvas.Canvas(pdf)
        y=800
        for line in report_text('MS 90 1 - Ca 12 1 -\nZn 50 1 -').splitlines():
            page.drawString(40,y,line)
            y-=18
        page.save()
        parsed = parse_pdf(pdf.getvalue())
        self.assertEqual(parsed.name, 'ALGODÃO CAROÇO')
        self.assertEqual(convert_report(parsed,'g/kg')[0]['Zn'], 0.005)

    @unittest.skipUnless(importlib.util.find_spec('scipy'), 'SciPy não está instalado neste ambiente')
    def test_solver_keeps_percent_units(self):
        import pandas as pd
        from src.solver import solve_least_cost
        items = pd.DataFrame([dict(ingredient_id='a',nome='A',preco_kg=1,
                                   inclusao_min=0,inclusao_max=100,EE=10,Cu=.005)])
        constraints = pd.DataFrame([dict(nutriente='Cu',minimo=.004,maximo=.006),
                                    dict(nutriente='EE',minimo=9,maximo=11)])
        result = solve_least_cost(items,constraints)
        self.assertTrue(result.success, result.message)
        copper = result.constraints.loc[result.constraints['nutriente'].eq('Cu')].iloc[0]
        self.assertAlmostEqual(float(copper['resultado']), .005)
        self.assertEqual(copper['unidade'], '%')


if __name__ == '__main__':
    unittest.main()
