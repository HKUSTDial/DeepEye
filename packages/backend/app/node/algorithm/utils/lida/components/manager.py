# Visualization manager class that handles the visualization of the data with the following methods

# summarize data given a df
# generate goals given a summary
# generate generate visualization specifications given a summary and a goal
# execute the specification given some data

import os
from typing import List, Union
import logging

import pandas as pd
from llmx import llm, TextGenerator
from lida.datamodel import Goal, Summary, TextGenerationConfig
from lida.utils import read_dataframe
from ..components.executor import ChartExecutor
from ..components.viz import VizGenerator, VizEditor, VizEvaluator, VizRepairer

logger = logging.getLogger("lida")


class Manager(object):
    def __init__(self, text_gen: TextGenerator = None) -> None:
        """
        Initialize the Manager object.

        Args:
            text_gen (TextGenerator, optional): Text generator object. Defaults to None.
        """

        self.text_gen = text_gen or llm()
        self.vizgen = VizGenerator()
        self.vizeditor = VizEditor()
        self.executor = ChartExecutor()
        self.evaluator = VizEvaluator()
        self.repairer = VizRepairer()
        self.data = None
        self.infographer = None

    def check_textgen(self, config: TextGenerationConfig):
        """
        Check if self.text_gen is the same as the config passed in. If not, update self.text_gen.

        Args:
            config (TextGenerationConfig): Text generation configuration.
        """
        if config.provider is None:
            config.provider = self.text_gen.provider or "openai"
            logger.info("Provider is not set, using default provider - %s", config.provider)
            return

        if self.text_gen.provider != config.provider:

            logger.info(
                "Switching Text Generator Provider from %s to %s",
                self.text_gen.provider,
                config.provider)
            self.text_gen = llm(provider=config.provider)


    def visualize(
        self,
        summary,
        goal,
        data,
        textgen_config: TextGenerationConfig = TextGenerationConfig(),
        #library="seaborn",
        library="matplotlib",
        return_error: bool = False,
    ):
        if isinstance(goal, dict):
            goal = Goal(**goal)
        if isinstance(goal, str):
            goal = Goal(question=goal, visualization=goal, chart_type="")

        self.check_textgen(config=textgen_config)
        code_specs = self.vizgen.generate(
            summary=summary, goal=goal, textgen_config=textgen_config, text_gen=self.text_gen,
            library=library)
        charts = self.execute(
            code_specs=code_specs,
            data=data,
            summary=summary,
            library=library,
            return_error=return_error,
        )
        return charts

    def execute(
        self,
        code_specs,
        data,
        summary: Summary,
        library: str = "seaborn",
        return_error: bool = False,
    ):
        if data is None:
            # 首先尝试直接读取文件名（可能是绝对路径或相对路径）
            try:
                data = read_dataframe(summary.file_name)
                print(f"成功从本地文件 {summary.file_name} 读取数据")
            except Exception as e:
                # 如果直接读取失败，尝试在当前目录查
                raise ValueError(f"无法读取数据文件: {summary.file_name}. 错误信息: {str(e)}")

        return self.executor.execute(
            code_specs=code_specs,
            data=data,
            summary=summary,
            library=library,
            return_error=return_error,
        )

    def edit(
        self,
        code,
        summary: Summary,
        instructions: List[str],
        textgen_config: TextGenerationConfig = TextGenerationConfig(),
        library: str = "seaborn",
        return_error: bool = False,
    ):
        """Edit a visualization code given a set of instructions

        Args:
            code (_type_): _description_
            instructions (List[Dict]): A list of instructions

        Returns:
            _type_: _description_
        """

        self.check_textgen(config=textgen_config)

        if isinstance(instructions, str):
            instructions = [instructions]

        code_specs = self.vizeditor.generate(
            code=code,
            summary=summary,
            instructions=instructions,
            textgen_config=textgen_config,
            text_gen=self.text_gen,
            library=library,
        )

        charts = self.execute(
            code_specs=code_specs,
            data=self.data,
            summary=summary,
            library=library,
            return_error=return_error,
        )
        return charts

    def repair(
        self,
        code,
        goal: Goal,
        summary: Summary,
        feedback,
        textgen_config: TextGenerationConfig = TextGenerationConfig(),
        library: str = "seaborn",
        return_error: bool = False,
    ):
        """ Repair a visulization given some feedback"""
        self.check_textgen(config=textgen_config)
        code_specs = self.repairer.generate(
            code=code,
            feedback=feedback,
            goal=goal,
            summary=summary,
            textgen_config=textgen_config,
            text_gen=self.text_gen,
            library=library,
        )
        charts = self.execute(
            code_specs=code_specs,
            data=self.data,
            summary=summary,
            library=library,
            return_error=return_error,
        )
        return charts

