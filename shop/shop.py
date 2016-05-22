#  Shop.py was created by Redjumpman for Redbot
#  This will create a data folder with 3 JSON files and 1 logger
#  The logger will contain information for admin use
import discord
import os
import json
import logging
from discord.ext import commands
from .utils.dataIO import fileIO
from __main__ import send_cmd_help
from .utils import checks
from time import strftime
try:   # Check if Tabulate is installed
    from tabulate import tabulate
    tabulateAvailable = True
except:
    tabulateAvailable = False

#  This is a global variable used for the time format
time_now = strftime("%Y-%m-%d %H:%M:%S")


class Shop:
    """Allows you to purchase items created by the Admins with your points"""
    # We have to define all the different files were going to load and save
    def __init__(self, bot):
        self.bot = bot
        self.players = fileIO("data/shop/players.json", "load")
        self.shop = fileIO("data/shop/shop.json", "load")
        self.pending = fileIO("data/shop/pending.json", "load")
        self.config = fileIO("data/shop/config.json", "load")

    # Create the group to store the shop commands
    @commands.group(name="shop", pass_context=True)
    async def _shop(self, ctx):
        """Individual Commands:
        ---------
        inventory      Shows a list of items in your inventory
        store          Shows a list of items for sale
        --------
        Pending List Commands:
        --------
        show           Shows a list of items waiting to be redeemed
        clear          Clear one single item from pending list
        clear all      Clears all items from the pending list
        -------
        Shop Commands:"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    # We want to seperate the store so it doesn't have a shop prefix
    @commands.command(pass_context=True, no_pm=True)
    async def store(self, ctx):
        """Shows a list of items that can be purchased"""
        # loads all the text in the file and dumps it into k
        shop_name = self.config["Shop Name"]
        column1 = []
        column2 = []
        for subdict in self.shop.values():
            column1.append(subdict['Item Name'])
        for subdict in self.shop.values():
            column2.append(subdict['Item Cost'])
        m = list(zip(column1, column2))
        t = tabulate(m, headers=["Item Name", "Item Cost"])
        header = "```"
        header += self.bordered(shop_name + " Store Listings")
        header += "```"
        await self.bot.whisper(header + "```\n" + t + "```")

    @_shop.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def add(self, ctx, cost: int, *, itemname):
        """Adds an item to the shop list"""
        shop_name = self.config["Shop Name"]
        self.shop[itemname] = {"Item Name": itemname, "Item Cost": cost}
        fileIO("data/shop/shop.json", "save", self.shop)
        await self.bot.say("```" + str(itemname) + " has been added to " +
                           shop_name + " shop for purchase." + "```")

    @_shop.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def remove(self, ctx, *, itemname):
        """Removes an item from the shop list"""
        shop_name = self.config["Shop Name"]
        if itemname in self.shop:
            del self.shop[itemname]
            fileIO("data/shop/shop.json", "save", self.shop)
            await self.bot.say("```" + str(itemname) + " has been removed from " +
                               shop_name + " shop." + "```")
        else:
            await self.bot.say("That item is not in " + shop_name + "'s store")

    @_shop.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def name(self, ctx, *, name):
        """Renames the shop"""
        shop_name = self.config["Shop Name"]
        if len(name) > 0:
            self.config["Shop Name"] = name
            fileIO("data/shop/config.json", "save", self.config)
            shop_name = self.config["Shop Name"]
            await self.bot.say("I have renamed the shop to " + shop_name)
        else:
            await self.bot.say("You need to enter a name for the shop")

    @_shop.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def toggle(self, ctx):
        """Opens and closes the shop"""
        shop_name = self.config["Shop Name"]
        if self.config["Shop Open"]:
            self.config['Shop Open'] = not self.config['Shop Open']
            fileIO("data/shop/config.json", "save", self.config)
            await self.bot.say("The shop is now closed")
        else:
            self.config["Shop Open"] = True
            fileIO("data/shop/config.json", "save", self.config)
            await self.bot.say(shop_name + " shop is now open for business!")

    @_shop.command(pass_context=True, no_pm=True)
    async def redeem(self, ctx, *, itemname):
        """Sends a request to redeem an item"""
        user = ctx.message.author
        if self.inventory_item_check(user.id, itemname):
            if self.inventory_item_amount(user.id, itemname):
                if user.id not in self.pending:
                    self.pending[user.id] = {}
                    fileIO("data/shop/pending.json", "save", self.pending)
                    self.pending[user.id][user.name] = {}
                    fileIO("data/shop/pending.json", "save", self.pending)
                    self.pending[user.id][user.name
                                          ][itemname
                                            ] = {"Item Name": itemname,
                                                 "Time Requested": time_now}
                    fileIO("data/shop/pending.json", "save", self.pending)
                    self.inventory_remove(user.id, itemname)
                    await self.bot.say("```" + itemname + " has been added " +
                                       "to pending list. Please wait for " +
                                       "approval before adding more of the " +
                                       "same item." + "```")
                else:
                    self.pending[user.id][user.name][itemname] = {"Item Name": itemname,
                                                                  "Time Requested": time_now}
                    fileIO("data/shop/pending.json", "save", self.pending)
                    self.inventory_remove(user.id, itemname)
                    msg = "```"
                    msg += itemname + " has been added to the"
                    msg += " pending list. Please wait for approval before "
                    msg += "adding more of the same item."
                    msg += "```"
                    await self.bot.say(msg)
            else:
                await self.bot.say("You do not have that item to redeem")
        else:
            await self.bot.say("You do not have that item to redeem")

    @_shop.command(pass_context=True, no_pm=True)
    async def buy(self, ctx, *, itemname):
        """Buy an item from the store list"""
        shop_name = self.config["Shop Name"]
        user = ctx.message.author
        if self.config["Shop Open"]:
            if self.inventory_check(user.id):
                if itemname in self.shop:
                    points = self.shop[itemname]["Item Cost"]
                    if self.account_check(user.id):
                        if self.enough_points(user.id, points):
                            points = self.shop[itemname]["Item Cost"]
                            if not self.inventory_item_check(user.id, itemname):
                                self.inventory_add(user.id, itemname)
                            self.inventory_add(user.id, itemname)
                            econ = self.bot.get_cog("Economy")
                            econ.withdraw_money(user.id, points)
                            msg = "```"
                            msg += "You have purchased a " + str(itemname)
                            msg += " for " + str(points) + " points. " + "\n"
                            msg += str(itemname) + " has been added to your inventory."
                            msg += "```"
                            await self.bot.say(msg)
                        else:
                            await self.bot.say("You don't have enough points to purchase this item")
                    else:
                        await self.bot.say("You do not have a bank account")
                else:
                    await self.bot.say("This item is not in the shop")
            else:
                await self.bot.say("You need to join the " + shop_name +
                                   " shop to purchase items." + " Example: !shop join")
        else:
            await self.bot.say(shop_name + " shop is currently closed")

    @_shop.command(pass_context=True, no_pm=True)
    async def gift(self, ctx, user: discord.Member, *, itemname):
        """Send a gift in your inventory to another member"""
        author = ctx.message.author
        if author == user:
            await self.bot.say("You can't give an item to yourself.")
            return
        if len(itemname) < 0:
            await self.bot.say("You need to tell me what you want to transfer")
            return
        if user.id in self.players:
            if self.inventory_item_check(author.id, itemname):
                if self.inventory_item_amount(author.id, itemname):
                    if itemname in self.players[user.id]["Inventory"]:
                        nametwo = self.shop[itemname]["Item Name"]
                        self.inventory_remove(author.id, itemname)
                        self.inventory_add(user.id, itemname)
                        logger.info("{}({}) gifted a {} item to {}({})".format(author.name, author.id, itemname, user.name, user.id))
                        await self.bot.say("```" + "I have gifted {} to {}'s inventory".format(nametwo, user.name) + "```")
                    else:
                        nametwo = self.shop[itemname]["Item Name"]
                        self.players[user.id]["Inventory"][itemname] = {"Item Name": nametwo,
                                                                        "Item Quantity": 0}
                        self.inventory_remove(author.id, itemname)
                        self.inventory_add(user.id, itemname)
                        logger.info("{}({}) gifted a {} item to {}({})".format(author.name, author.id, itemname, user.name, user.id))
                        await self.bot.say("```" + "I have gifted {} to {}'s inventory".format(nametwo, user.name) + "```")
                else:
                    await self.bot.say("You currently don't own any of these.")
            else:
                await self.bot.say("You do not own this shop item.")
        else:
            shop_name = self.config["Shop Name"]
            await self.bot.say("I cant find a user with that name." +
                               " Check to see if that user has joined " + shop_name +
                               " shop. They need to type <p>shop join before they can recieve a gift")

    @_shop.command(pass_context=True, no_pm=True)
    async def join(self, ctx):
        """Adds you to the shop. Only need to do this once."""
        shop_name = self.config["Shop Name"]
        user = ctx.message.author
        if user.id not in self.players:
            self.players[user.id] = {}
            fileIO("data/shop/players.json", "save", self.players)
            self.players[user.id]["Inventory"] = {}
            fileIO("data/shop/players.json", "save", self.players)
            await self.bot.say("\n" + "```" + "You have" +
                               " joined " + shop_name + " shop. You can now buy" +
                               " items with points." + "```")
        else:
            await self.bot.say("```" + "You have already joined" + "```")

    @commands.group(name="pending", pass_context=True)
    async def _pending(self, ctx):
        """List of pending commands for redemable items"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_pending.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def show(self, ctx):
        """Shows a list of items waiting to be redeemed"""
        if len(self.pending) > 0:
            k = json.dumps(self.pending, indent=1, sort_keys=True)
            m = "```"
            m += k.replace('"', '',).replace('{', '').replace('}', '').replace(',', '')
            m += "```"
            await self.bot.say(m)
        else:
            await self.bot.say("The pending list is empty.")

    @_pending.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def clear(self, ctx, user: discord.Member, *, itemname):
        """Allows you to clear one item from the pending list"""
        if len(self.pending) > 0:
            if user.id in self.pending:
                if itemname in self.pending[user.id][user.name]:
                    del self.pending[user.id][user.name][itemname]
                    fileIO("data/shop/pending.json", "save", self.pending)
                    await self.bot.say(itemname + "has been cleared from" +
                                       " pending, for " + user.name +
                                       "'s redeem request.")
                else:
                    await self.bot.say("The item is not in the pending list" +
                                       " for this user")
            else:
                await self.bot.say("This user has no pending requests. Make" +
                                   " sure their name is spelled correctly.")
        else:
            await self.bot.say("The pending list is empty")

    @_pending.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def clearall(self, ctx):
        """Clears all items from the pending list"""
        if len(self.pending) > 0:
            del self.pending
            self.pending = {}
            fileIO("data/shop/pending.json", "save", self.pending)
            await self.bot.say("Pending list now cleared")
        else:
            await self.bot.say("Nothing in pending list to clear")

    @commands.command(pass_context=True, no_pm=True)
    async def inventory(self, ctx):
        """Shows a list of items you have purchased"""
        user = ctx.message.author
        if user.id in self.players:
            if self.players[user.id]["Inventory"] is None:
                await self.bot.say("You have not purchased any items for " +
                                   "me to display")
            else:
                    column1 = []
                    column2 = []
                    for subdict in self.players[user.id]["Inventory"].values():
                            column1.append(subdict["Item Name"])
                    for subdict in self.players[user.id]["Inventory"].values():
                            column2.append(subdict["Item Quantity"])
                    m = list(zip(column1, column2))
                    t = tabulate(m, headers=["Item Name", "Item Quantity"])
                    header = "```"
                    header += self.bordered("I N V E N T O R Y")
                    header += "```"
                    await self.bot.whisper(header + "```\n" + t + "```")

    def bordered(self, text):
        lines = text.splitlines()
        width = max(len(s) for s in lines)
        res = ['┌' + '─' * width + '┐']
        for s in lines:
            res.append('│' + (s + ' ' * width)[:width] + '│')
        res.append('└' + '─' * width + '┘')
        return '\n'.join(res)

    def account_check(self, uid):
        econ = self.bot.get_cog('Economy')
        if econ.account_check(uid):
            return True
        else:
            return False

    def enough_points(self, uid, amount):
        econ = self.bot.get_cog('Economy')
        if self.account_check(uid):
            if econ.enough_money(uid, amount):
                return True
            else:
                return False

    def inventory_check(self, uid):
        if uid in self.players:
            return True
        else:
            return False

    def inventory_item_check(self, uid, itemname):
        if self.inventory_check(uid):
            if itemname in self.players[uid]["Inventory"]:
                return True
            else:
                return False
        else:
            False

    def inventory_item_amount(self, uid, itemname):
            if self.inventory_check(uid):
                if self.inventory_item_check(uid, itemname):
                    if self.players[uid]["Inventory"][itemname]["Item Quantity"] > 0:
                        return True
                    else:
                        return False
                else:
                    return False
            else:
                return False

    def inventory_add(self, uid, itemname):
        if self.inventory_check(uid):
            if self.inventory_item_check(uid, itemname):
                self.players[uid]["Inventory"][itemname]["Item Quantity"] += 1
                fileIO("data/shop/players.json", "save", self.players)
            else:
                self.players[uid]["Inventory"][itemname] = {"Item Name": itemname,
                                                            "Item Quantity": 1}
                fileIO("data/shop/players.json", "save", self.players)
        else:
            return False

    def inventory_remove(self, uid, itemname):
        if self.inventory_check(uid):
            if self.inventory_item_check(uid, itemname):
                self.players[uid]["Inventory"][itemname]["Item Quantity"] -= 1
                fileIO("data/shop/players.json", "save", self.players)
            else:
                return False
        else:
            return False


def check_folders():
    if not os.path.exists("data/shop"):
        print("Creating data/shop folder...")
        os.makedirs("data/shop")


def check_files():
    system = {"Shop Name": "RedJumpman",
              "Shop Open": True}

    f = "data/shop/pending.json"
    if not fileIO(f, "check"):
        print("Creating default shop pending.json...")
        fileIO(f, "save", {})

    f = "data/shop/shop.json"
    if not fileIO(f, "check"):
        print("Creating default shop shop.json...")
        fileIO(f, "save", {})

    f = "data/shop/players.json"
    if not fileIO(f, "check"):
        print("Adding shop player.json...")
        fileIO(f, "save", {})

    f = "data/shop/config.json"
    if not fileIO(f, "check"):
        print("Adding shop config.json...")
        fileIO(f, "save", system)
    else:  # consistency check
        current = fileIO(f, "load")
        if current.keys() != system.keys():
            for key in system.keys():
                if key not in current.keys():
                    current[key] = system[key]
                    print("Adding " + str(key) +
                          " field to shop config.json")
            fileIO(f, "save", current)


def setup(bot):
    global logger
    check_folders()
    check_files()
    logger = logging.getLogger("shop")
    if logger.level == 0:  # Prevents the logger from being loaded again in case of module reload
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename='data/shop/shop.log', encoding='utf-8', mode='a')
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    if tabulateAvailable:
        bot.add_cog(Shop(bot))
    else:
        raise RuntimeError("You need to run 'pip3 install tabulate'")