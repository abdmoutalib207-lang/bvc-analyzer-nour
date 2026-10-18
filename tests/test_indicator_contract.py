"""Independent Wilder arithmetic and Python/browser parity on available histories."""
from datetime import date, timedelta
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from nour.analytics import technical

ROOT = Path(__file__).resolve().parents[1]


class IndicatorContract(unittest.TestCase):
    def test_wilder_is_distinct_from_the_preserved_simple_atr(self):
        # A single wide bar leaves the rolling SMA but remains in Wilder's state.
        bars = [dict(d=(date(2025,1,1)+timedelta(days=i)).isoformat(),
                     o=100,h=150 if i==14 else 101,l=50 if i==14 else 99,c=100,v=10)
                for i in range(30)]
        result = technical({'candles':bars})
        self.assertEqual(result['atr14'],2)
        expected=2
        for i in range(14,30):
            expected=(13*expected+(100 if i==14 else 2))/14
        self.assertEqual(result['atr14_wilder'],round(expected,2))
        self.assertGreater(result['atr14_wilder'],result['atr14'])
        self.assertEqual(result['atr14_wilder_pct'],result['atr14_wilder'])
        self.assertIsNone(technical({'candles':bars[:13]})['atr14_wilder'])
        self.assertEqual(technical({'candles':bars[:14]})['atr14_wilder'],2)
        self.assertIsNone(technical({'candles':bars[:14]})['atr14'])

    def test_existing_indicators_on_an_exact_linear_price_series(self):
        bars=[dict(o=c,h=c+1,l=c-1,c=c,v=10) for c in range(2,62)]
        result=technical({'candles':bars})
        self.assertEqual(result['sma20'],51.5)
        self.assertEqual(result['sma50'],36.5)
        self.assertEqual(result['rsi14'],100)
        self.assertEqual(result['macd'],7)
        self.assertEqual(result['macd_signal'],7)
        self.assertEqual(result['atr14'],2)
        self.assertEqual(result['ema20'],51.5)
        self.assertEqual(result['ema50'],36.5)
        self.assertIsNone(result['sma200'])

    def test_chart_matches_canonical_metrics_and_resumption_on_all_titles(self):
        fixture=json.loads((ROOT/'data/market_snapshot.json').read_text())
        cases=[]
        mapping={'rsi14':'rsi','macd_signal':'signal','bollinger_upper':'upper','bollinger_lower':'lower'}
        for symbol,record in fixture['records'].items():
            bars=record.get('candles') or []
            # Same already-validated bars exposed by the graph.
            valid=[b for b in bars if all(isinstance(b.get(k),(int,float)) and not isinstance(b.get(k),bool) for k in ('o','h','l','c','v'))
                   and min(b['o'],b['h'],b['l'],b['c'])>0 and b['h']>=max(b['o'],b['l'],b['c']) and b['l']<=min(b['o'],b['c']) and b['v']>=0]
            since=''
            if record.get('resumed_recently'):
                n=record.get('sessions_since_resume')
                since=valid[-n]['d'] if isinstance(n,int) and n>0 and len(valid)>=n else '9999-12-31'
            computed=technical({**record,'candles':valid})
            expected={mapping.get(k,k):computed[k] for k in ('sma20','sma50','sma200','ema20','ema50','rsi14','macd','macd_signal','atr14_wilder','bollinger_upper','bollinger_lower')}
            cases.append({'symbol':symbol,'bars':[[b[k] for k in ('d','o','h','l','c','v')] for b in valid], 'since':since,'expected':expected})
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'cases.json';path.write_text(json.dumps(cases))
            js="""const fs=require('node:fs'),assert=require('node:assert/strict');
            const {indicators}=require('./web/chart-controls.js');
            for(const c of JSON.parse(fs.readFileSync(process.argv[1]))){
              const values=indicators(c.bars,c.since),last=values.at(-1)||{};
              for(const [k,v] of Object.entries(c.expected)){
                if(v===null)assert.equal(last[k]??null,null,c.symbol+' '+k);
                else assert.ok(Number.isFinite(last[k])&&Math.abs(last[k]-v)<=0.005001,c.symbol+' '+k+' '+last[k]+' / '+v);
              }
              const prefix=c.bars.slice(0,Math.min(35,c.bars.length));
              assert.deepEqual(indicators(prefix,c.since),values.slice(0,prefix.length),'No future values may affect the prefix');
            }"""
            subprocess.run(['node','-e',js,str(path)],cwd=ROOT,check=True,capture_output=True)


if __name__=='__main__':
    unittest.main()
