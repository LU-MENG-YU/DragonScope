import unittest
from datetime import date

from collectors.sources import cpbl, cpbl_stats, venues, weather


class CPBLNormalizationTests(unittest.TestCase):
    def test_normalize_dragons_game(self):
        raw = {
            'GameDate': '2026-09-20T00:00:00',
            'PreExeDate': '2026-09-20T17:05:00',
            'GameSno': 123,
            'Pkno': '2026A0123',
            'GameSeasonCode': '2',
            'VisitingTeamCode': 'AAA011',
            'HomeTeamCode': 'ACN011',
            'FieldAbbe': '洲際',
            'VisitingScore': 4,
            'HomeScore': 6,
            'GameStatus': 3,
            'GameStatusChi': '比賽結束',
            'WinningPitcherName': '甲',
            'LoserPitcherName': '乙',
        }
        game, venue, event = cpbl._normalize_game(raw, year=2026, kind='A', level='一軍', today=date(2026, 9, 23))
        self.assertEqual(game['status'], 'FINAL')
        self.assertEqual(game['away_team'], '味全龍')
        self.assertEqual(game['date'], '2026-09-20')
        self.assertIn('4 : 6', event['title'])
        self.assertEqual(event['venue_id'], venue['id'])

    def test_lineup_extracts_dragons(self):
        game = {
            'id': 'cpbl-2026-A-1', 'date': '2026-09-20', 'start_time': '17:05',
            'level': '一軍', 'away_team_code': 'AAA', 'home_team_code': 'ACN',
            'url': 'https://example.test', 'venue_id': 'v-x'
        }
        rows = []
        for i in range(1, 10):
            rows.append({'TeamNo': 'AAA011', 'Lineup': i, 'CHName': f'龍{i}', 'Acnt': f'{i:010d}', 'UniformNo': str(i), 'DefendStation': '8'})
        rows.append({'TeamNo': 'AAA011', 'Lineup': 0, 'CHName': '龍投手', 'Acnt': '0000009999', 'UniformNo': '99', 'DefendStation': '1'})
        ls, es, ps = cpbl._lineup_payload({'FirstSnoJson': rows}, game)
        self.assertEqual(len(ls), 1)
        self.assertEqual(len(ls[0]['batting_order']), 9)
        self.assertIn('龍投手', ls[0]['players'])
        self.assertTrue(any(p['position_group'] == '投手' for p in ps))
        self.assertEqual(es[0]['type'], 'LINEUP')


class CPBLStatsTests(unittest.TestCase):
    def test_extract_public_player_object(self):
        obj = '{"acnt":"0000001234","chName":"測試龍將","engname":"Test","uniformNo":"7","defendStation":"6","retiredDate":null,"team":{"code":"AAA","name":"味全龍"}}'
        players = cpbl_stats._extract_players(obj)
        self.assertEqual(len(players), 1)
        self.assertEqual(players[0]['position_group'], '內野手')
        self.assertEqual(players[0]['id'], 'cpbl-0000001234')
        self.assertNotIn('level', players[0])


class VenueWeatherTests(unittest.TestCase):
    def test_venue_registry_enriches_tianmu(self):
        result = venues.collect({})
        tianmu = next(v for v in result.payload['venues'] if v.get('source_name') == '天母')
        self.assertEqual(tianmu['city'], '臺北市')
        self.assertFalse(tianmu['indoor'])
        self.assertIn('latitude', tianmu)

    def test_weather_nearest_hour(self):
        times = ['2026-09-24T18:00', '2026-09-24T19:00']
        self.assertEqual(weather._nearest_hour_index(times, '2026-09-24', '18:35'), 1)
        self.assertEqual(weather._wmo_text(61), '雨')


if __name__ == '__main__':
    unittest.main()
