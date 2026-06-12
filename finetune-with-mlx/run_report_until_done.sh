#!/bin/zsh
# Watchdog: gemma2:2b wedges the Ollama runner after sustained load (~6-7 questions),
# but a fresh restart cures it. So we score in small batches, restarting Ollama before
# each batch. The report resumes from its JSONL cache, so batches compose into a full run.
set -u
cd /Users/ansarmuhammad/Desktop/finetune-with-mlx
source venv/bin/activate

BATCH=1          # one question per fresh Ollama runner — a poison question can't
                 # wedge its neighbors, and skip-on-failure stops re-hitting it
MAXCYCLES=120
ADAPTER=adapters_v5
JUDGE=gemma2:2b

scored() {  # echo count of fully-scored questions
  python3 - <<'PY'
import json
rows=[json.loads(l) for l in open("report_cache_adapters_v5.jsonl") if l.strip()]
isnum=lambda x:isinstance(x,(int,float))
print(sum(all(isnum(r.get(k)) for k in("base_rel","base_cor","ft_rel","ft_cor")) for r in rows))
PY
}

for cycle in $(seq 1 $MAXCYCLES); do
  done_n=$(scored)
  echo "=== cycle $cycle | fully scored: ${done_n}/83 ==="
  if [ "$done_n" -ge 83 ]; then echo "ALL DONE"; break; fi

  # fresh Ollama runner
  osascript -e 'quit app "Ollama"' 2>/dev/null
  pkill -9 -x ollama 2>/dev/null; pkill -9 -f "ollama runner" 2>/dev/null
  sleep 3
  open -a Ollama
  for i in $(seq 1 20); do
    sleep 3
    curl -s --max-time 4 http://localhost:11434/api/version >/dev/null 2>&1 && break
  done
  # warm the judge (cold load)
  curl -s --max-time 120 http://localhost:11434/api/generate \
    -d "{\"model\":\"$JUDGE\",\"prompt\":\"OK\",\"stream\":false}" >/dev/null 2>&1

  # one batch; resumes from cache, writes md after every eval
  python generate_report.py --adapter "$ADAPTER" --judge-model "$JUDGE" --max-new "$BATCH"
done

echo "=== final: $(scored)/83 fully scored ==="
