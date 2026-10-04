PY ?= python3
BUILD := build
EXAMPLES := examples

.PHONY: all test gate demo clean install

all: test

test:
	$(PY) -m unittest discover -s tests

# 门禁：测试 + 三个示例必须真的能渲出来（退出码必须是 0）
gate: test
	@echo "--- 门禁：示例可渲染 ---"
	$(PY) -m soundtrack check $(EXAMPLES)/ui-fx.json
	$(PY) -m soundtrack check $(EXAMPLES)/menu-loop.json
	$(PY) -m soundtrack render --help > /dev/null
	@echo "gate ok"

demo: gate
	@mkdir -p $(BUILD)
	$(PY) -m soundtrack render $(EXAMPLES)/ui-fx.json -o $(BUILD)/ui-fx.wav
	$(PY) -m soundtrack render $(EXAMPLES)/menu-loop.json -o $(BUILD)/menu-loop.wav
	$(PY) -m soundtrack adapt $(EXAMPLES)/timeline-cues.json -o $(BUILD)/timeline.wav
	@ls -lh $(BUILD)

install:
	$(PY) -m pip install .

clean:
	rm -rf $(BUILD) build
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete
