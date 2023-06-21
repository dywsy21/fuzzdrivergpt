# What is FuzzDriverGPT?

`fuzzdrivergpt` is a GPT-based fuzz driver generator.
It is a tool aims to generate effective fuzz drivers for guys who want to fuzz some library APIs.
Ideally, an effective fuzz driver is a piece of high quality API usage code which can sufficiently test the given APIs without raising any false positive (bugs caused by the driver code).

Currently, `fuzzdrivergpt`:
- generates prompts utilizing multiple sources of API usage knowledge
- can validate the effectiveness of the generated fuzz drivers
- can iteratively fix/improve the generated drivers
- provides several use modes from one-round generation to repeatedly search valid drivers

The query strategies haven been tested on 86 APIs from 30 C projects of oss-fuzz, and some strategies can generate effective drivers for 78 (91%) of them with manually refined validation criteria.

## Video demo

The demo video shows the process of using iterative query strategy to generate valid fuzz drivers for `md_html` from project `md4c`.

## Generated fuzz drivers

See [`examples`](https://github.com/occia/fuzzdrivergpt/tree/main/examples).


# Usage Guidance

## Prerequisites

- get your [openai api key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-secret-api-key), and configure it into the `openaikey.txt` (it is ignored by git)

```bash
# content of openaikey.txt
OPENAI_APIKEY = your-openai-apikey
OPENAI_ORGID = your-orgid
```

- download [crawled usage](https://drive.google.com/file/d/1c3MaOKmSiPikHlQkVl8TSjLL1zCpv5NO/view?usp=sharing) for supported projects, save as `./meta/crawled_usage.json` (6.6GB example usage for 30 projects based on [sourcegraph](https://sourcegraph.com/search), we will eliminate this step in the near future)

- install `jdk-19.0.2` into `./tools/jdk-19.0.2`

```bash
wget https://download.java.net/java/GA/jdk19.0.2/fdb695a9d9064ad6b064dc6df578380c/7/GPL/openjdk-19.0.2_linux-x64_bin.tar.gz
tar xf openjdk-19.0.2_linux-x64_bin.tar.gz
mv jdk-19.0.2 tools/
# remove the downloed if you want
rm openjdk-19.0.2_linux-x64_bin.tar.gz
```

- install python requirements

```bash
# one-time installation
mkdir venv
virtualenv -p `which python3` venv
. venv/bin/activate
pip install -r requirements.txt
deactivate

# enter the python env 
. venv/bin/activate
# leave the python env 
deactivate
```

## Usage 

Before generating, you need to prepare the analysis environment and execution environment. Currently, we provided environment for 30 OSS-Fuzz C projects. We're refining this to make the environment preparation more general and painless.

For supported projects, run the following command (we use `md4c` as an example):
```bash
python prepareOSSFuzzImage.py -t fuzzdrivergpt-env md4c
```

Here are multiple ways to generate fuzz drivers using `fuzzdrivergpt` for a given API.

### One-Round Mode: Generate-only

The following command queries a prompt generated by BACTX query strategy, and save the code returned by GPT model into the specified json.

```bash
python main.py -l c -m gpt-4-0314 -t md4c -f md_html -q BACTX -DV -o test.json
# Expected Output: test_round1.json
```

### One-Round Mode: Generate and validate

The following command queries a prompt generated by BACTX query strategy, validates the code returned by GPT model, and saves all detail into the specified json.

```bash
python main.py -l c -m gpt-4-0314 -t md4c -f md_html -q BACTX -o test.json
# Expected Output: test_round1.json
```

### One-Round Mode: Iteratively generate, validate, and fix until succeed or maximum iterations are reached

For the following command, it does:

- 1) Query a prompt generated by BACTX query strategy
- 2) Validate the code returned by GPT model
- 3) If the code passes the validation or the the maxiteration (20 in the case) is reached, stop and save all detail into the specified json
- 4) Otherwise, propose a fix prompt based on the error, then goto 2).

```bash
python main.py -l c -m gpt-4-0314 -t md4c -f md_html -q ITER-BA -MI 20 -o test.json
# Expected Output: test_round1.json
```

### Search Mode: Repeatedly do one-round mode until succeed or maximum rounds are reached

All the processes of the above commands can be repeatedly done to search for valid drivers by adding `-MR MAXROUNDS`.
For example. the following repeats the above iterative query process for at most 3 times.

```bash
python main.py -l c -m gpt-4-0314 -t md4c -f md_html -q ITER-BA -MI 20 -MR 3 -o test.json
# Expected Output: test_round1.json, test_round2.json, test_round3.json, 
```

### Result interpretation

- Read summary from command line output (coming soon)
- View whole taxonomized detail in local website (coming soon)


# Technical Overview

## Query strategies

A query strategy defines a way to generate prompt(s). The following table lists all strategies integrated into `fuzzdrivergpt` and you can pick one depending on what you have.
The strategies of `fuzzdrivergpt` are motivated by the findings of our recent [research](https://github.com/occia/fuzzdrivergpt) on the pros and cons of various LLM-based fuzz driver generation strategies. 
In our evaluation, the iterative strategies have best performance but their potential GPT costs can be high.

|Query Strategy| API Decl| API Doc| Example Code| Iterative Fix|
| ---          | ---     | ---    | ---         | ---          |
| NAIVE        | &cross; | &cross;| &cross;     | &cross;      |
| BACTX        | &check; | &cross;| &cross;     | &cross;      |
| DOCTX        | &check; | &check;| &cross;     | &cross;      |
| UGCTX        | &check; | &cross;| &check;     | &cross;      |
| ITER-BA      | &check; | &cross;| &cross;     | &check;      |
| ITER-ALL     | &check; | &check;| &check;     | &check;      |

## Effectivenss validation

Automatically validating a fuzz driver is effective or not in scale is challengable since it requires the deep understanding of target API semantics.
In general, `fuzzdrivergpt` validates a fuzz driver by first compiling the driver code and then fuzzing it for a short time period, e.g., 1 min, with empty seed corpus.
If the fuzzing ends without finding any bug, it is a valid driver.
The intuition here is that the driver is not likely to find crash under a poor fuzzing setup.
Obviously this does not suit every case.
For advanced users who want to search more and filter hard for better driver generation, `fuzzdrivergpt` will support configurable validation criteria soon.


# Todo

- Easier to use
	- [ ] More documentation
	- [ ] New process/interface for API targets out of OSS-Fuzz projects
	- [ ] Automation for API usage collection
	- [ ] Refine the heavy, manual prerequisites installation process

- More functionality
	- [ ] Driver enhance mode (not generate from scratch but from a working one!)
	- [ ] Manual configuration of the driver effectiveness validation 

- More programming languages


# License

MIT License, see LICENSE.txt.


# I Want to Contribute!

Feel free to file an issue for suggestion, contribution, or discussion for `fuzzdrivergpt`.

Contributors:
- [Cen Zhang](https://www.github.com/occia)
- [Mingqiang Bai](https://www.github.com/7zq12lvm-b)
