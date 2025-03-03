import os
import yaml

from openai import OpenAI

if __name__ == '__main__':
  cfg = yaml.load(open('../config.yaml'), yaml.FullLoader)
  print(cfg)

  #model = "gemini-2.0-flash-thinking-exp-01-21"
  model = "deepseek-reasoner-alpha-data-process"
  client = OpenAI(
      api_key=cfg["OPENAI_API_KEY"],
      base_url=cfg['OPENAI_API_BASE'],
  )

  chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "我是一个来自中国的大语言模型，你想和我说什么",
        }
    ],
    model=model,
  )
  print(chat_completion.choices[0].message.content)


