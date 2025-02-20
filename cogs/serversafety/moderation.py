# Free RT - Moderation

from discord.ext import commands
from discord import app_commands

from util import RT


class Moderation(commands.Cog):
    def __init__(self, bot: RT):
        self.bot = bot

    @commands.hybrid_command(
        extras={
            "headding": {
                "ja": "メンバーのBAN",
                "en": "BAN members"
            }, "parent": "ServerSafety"
        }, aliases=["バン", "ばん", "BAN"]
    )
    @commands.has_guild_permissions(ban_members=True)
    @app_commands.describe(members="対象のメンバー")
    async def ban(
        self, ctx, *, members: str
    ):
        """!lang ja
        --------
        メンバーをBANできます。

        Parameters
        ----------
        members : メンバーのメンションか名前
            誰をBANするかです。  
            カンマで区切って複数人指定もできます。

        !lang en
        --------
        Ban members

        Parameters
        ----------
        members : Mention or Name of members
            Target members.

        Examples
        --------
        `rf!ban @tasuren @tasuren-sub`"""
        mode = "ban"
        members = [
            await commands.UserConverter().convert(ctx, member)
            for member in members.split(",")
        ]
        excepts = []
        for m in members:
            try:
                await getattr(ctx.guild, mode)(m, reason=f"free RT コマンド / 実行者:{ctx.author}")
            except Exception:
                excepts.append(m)
        if excepts:
            mode = mode.upper()
            await ctx.reply(
                f"{mode}を実行しました。\n(しかし、{', '.join(map(str, excepts))}の{mode}に失敗しました。)",
                delete_after=5
            )
        else:
            await ctx.reply("ok", delete_after=5)

    @commands.has_permissions(kick_members=True)
    @commands.hybrid_command(
        extras={
            "headding": {
                "ja": "メンバーのキック",
                "en": "Kick members"
            }, "parent": "ServerSafety"
        }, aliases=["キック", "きっく", "KICK"]
    )
    @app_commands.describe(members="対象のメンバー")
    async def kick(self, ctx, *, members):
        """!lang ja
        --------
        メンバーをキックできます。

        Parameters
        ----------
        members : メンバーのメンションか名前
            誰をBANするかです。  
            カンマで区切って複数人指定もできます。

        !lang en
        --------
        Kick members.

        Parameters
        ----------
        members : Mention or Name of members
            Target members.

        Examples
        --------
        `rf!ban @tasuren @tasuren-sub`"""
        await self.ban(ctx, members=members, mode="kick")

    kick._callback.__doc__ = ban._callback.__doc__.replace("ban", "kick").replace("BAN", "Kick") \
        .replace("Ban", "Kick")


async def setup(bot):
    await bot.add_cog(Moderation(bot))
