import discord
import os
import time
from discord.ext import commands
from discord import app_commands, ui
from discord.ui import button, Button, View, Modal, TextInput
from collections import Counter
import asyncio
import random
import requests
import string
import tok
from tok import TOKEN, DATABASE1, DATABASE2
from pymongo import MongoClient
from discord import File
from discord.ext.commands import BucketType

intents = discord.Intents.default()
intents.dm_messages = True
intents.messages = True
intents.message_content = True
intents.guilds = True

# DATABASE2 is defined in tok.py with its password and username. You can setup your own database with these 3 lines.
# We use database to store all the feedback in there.
mongo_client = MongoClient(DATABASE2)
dbb = mongo_client['coding_round_feedback']
collection = dbb['feedback']

class FeedbackModal(Modal):
    def __init__(self, problem_label: str, server_id: int):
        super().__init__(title=f"Feedback for {problem_label}")
        self.problem_label = problem_label
        self.server_id = server_id
        self.feedback_input = TextInput(
            label="Your Feedback",
            style=discord.TextStyle.paragraph,
            placeholder="Enter your feedback here...",
            required=True,
            #leave this at 2000 to avoid issues with reaching discord message limit.
            max_length=2000 
        )
        self.add_item(self.feedback_input)
    async def on_submit(self, interaction: discord.Interaction):
        feedback = self.feedback_input.value
        user = interaction.user
        server_id = interaction.guild.id

        user_feedback_count = collection.count_documents({"username": user.name, "server_id": server_id})
        #This number shows how many active feedbacks a user can have in a specific server
        if user_feedback_count >= 30:
            await interaction.response.send_message("You have reached the limit of 30 feedback submissions.", ephemeral=True)
            return

        collection.insert_one({
            "problem_label": self.problem_label,
            "server_id": server_id,
            "username": user.name,
            "feedback": feedback
        })

        server_feedback_count = collection.count_documents({"server_id": server_id})
         #How many total feedback do you want before it automatically deletes all feedbacks?
        if server_feedback_count >= 500:
            collection.delete_many({"server_id": server_id})

        await interaction.response.send_message(f"Thank you for your feedback on {self.problem_label}!", ephemeral=True)

class FeedbackButton(View):
    def __init__(self, problem_label: str, server_id: int):
        super().__init__(timeout=None) 
        self.problem_label = problem_label
        self.server_id = server_id

        button = Button(label="Submit Feedback", style=discord.ButtonStyle.green, custom_id=f"submit_feedback_button_{self.problem_label}")
        button.callback = self.submit_feedback 
        self.add_item(button)

    async def submit_feedback(self, interaction: discord.Interaction):
        server_id = interaction.guild.id
        await interaction.response.send_modal(FeedbackModal(self.problem_label, server_id))

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=commands.when_mentioned_or('!'), intents=intents)

    async def setup_hook(self) -> None:
        server_ids = collection.distinct("server_id")
        # Add titles here. What do you want the bot to title the feedback messages?
        # If a title is not here it'll still work, but old feedback messages won't work after the bot is restarted.
        problem_labels = ["A", "A1", "A2", "A3", "B", "B1", "B2", "B3", "C", "C1", "C2", "C3", "D", "D1", "D2", "D3", "E", "E1", "E2", "E3", "F", "F1", "F2", "F3", "G", "G1", "G2", "G3", "H", "H1", "H2", "H3", "Bot"]  # Add or modify as needed

        for server_id in server_ids:
            for problem in problem_labels:
                self.add_view(FeedbackButton(problem, server_id))
    async def on_ready(self):
        print(f"We have logged in as {self.user}")
client = MyBot()

@client.command(name="sendfeedback")
@commands.cooldown(1, 10, BucketType.user) 
@commands.has_permissions(administrator=True)
async def send_feedback_message(ctx: commands.Context, problems: str):
    print(f"Command received: !sendfeedback {problems}")
    server_id = ctx.guild.id
    problem_list = problems.split(",") 

    for problem in problem_list:
        problem = problem.strip() 
        if problem:
            view = FeedbackButton(problem, server_id)
            await ctx.send(f"Submit your feedback for {problem}:", view=view)
            print(f"Sent feedback button for {problem}.") 

@client.command(name="viewfeedback")
@commands.cooldown(1, 10, BucketType.user) 
@commands.has_permissions(administrator=True)
async def view_feedback(ctx: commands.Context, problem: str):
    server_id = ctx.guild.id
    feedback_list = list(collection.find({"problem_label": problem, "server_id": server_id}))
    print(server_id)
    print(problem)
    if feedback_list:
        feedback_message = f"Feedback for {problem}:\n"
        chunk = ""
        for feedback in feedback_list:
            feedback_entry = f"- {feedback['username']}: {feedback['feedback']}\n"
            if len(chunk) + len(feedback_entry) > 2000:
                await ctx.send(chunk)
                chunk = feedback_entry
            else:
                chunk += feedback_entry
        if chunk:
            await ctx.send(chunk)
    else:
        await ctx.send(f"No feedback yet for {problem}.")

@client.command(name="cleardatabase")
@commands.cooldown(1, 10, BucketType.user) 
@commands.has_permissions(administrator=True)
async def clear_database(ctx: commands.Context):
    server_id = ctx.guild.id
    #Add feedback message titles here as well
    feedback_problems = ["A", "A1", "A2", "A3", "B", "B1", "B2", "B3", "C", "C1", "C2", "C3", "D", "D1", "D2", "D3", "E", "E1", "E2", "E3", "F", "F1", "F2", "F3", "G", "G1", "G2", "G3", "H", "H1", "H2", "H3", "Bot"]
    for problem in feedback_problems:
        collection.delete_many({"problem_label": problem, "server_id": server_id})
    await ctx.send("Database cleared for this server!")

client.run(TOKEN)
