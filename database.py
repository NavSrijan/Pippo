import asyncpg
import datetime
import json


class Database():

    def __init__(self, pool):
        self.pool = pool

    async def execute(self, sql, *args):
        async with self.pool.acquire() as con:
            q = await con.execute(sql, *args)
        return q
        
    async def update_or_insert(self, sql, sql2, *args):
        q = await self.execute(sql, *args)
        if q=="UPDATE 0":
            await self.execute(sql2, *args)

    async def view(self, sql, *args):
        async with self.pool.acquire() as con:
            result = await con.fetch(sql, *args)
        return result


class Servers(Database):
    """
    CREATE TABLE "servers" (
	"server_id" BIGINT NOT NULL,
	"prefix" TEXT,
	PRIMARY KEY ("server_id")
    );
    """

    def __init__(self, pool):
        self.tableName = "servers"
        super().__init__(pool)

    async def prefix_add(self, server_id, prefix):
        """Add a server's prefix to database"""
        await self.execute(
            "INSERT INTO servers (server_id, prefix) VALUES ($1, $2) "
            "ON CONFLICT (server_id) DO UPDATE SET prefix = EXCLUDED.prefix;",
            server_id, prefix,
        )

    async def ensure_server(self, server_id, prefix="."):
        """Add a server if missing without overriding existing custom prefix."""
        await self.execute(
            "INSERT INTO servers (server_id, prefix) VALUES ($1, $2) "
            "ON CONFLICT (server_id) DO NOTHING;",
            server_id, prefix,
        )

    async def get_all_servers(self):
        """Fetch all recorded server records from database"""
        sql = f"SELECT server_id, prefix FROM {self.tableName};"
        return await self.view(sql)

    async def fetch_prefix(self, server_id):
        """Fetch a server's prefix from database"""
        sql = f"SELECT prefix FROM {self.tableName} WHERE server_id=$1;"
        res = await self.view(sql, server_id)
        if len(res) != 0:
            return res[0][0]
        else:
            return "."

class Greetings(Database):
    """
CREATE TABLE "greetings" (
	"user_id" BIGINT NOT NULL,
	"gm" BOOLEAN NOT NULL,
	"ga" BOOLEAN NOT NULL,
	"ge" BOOLEAN NOT NULL,
	"gn" BOOLEAN NOT NULL,
	PRIMARY KEY ("user_id")
);
    """
    def __init__(self, pool):
        self.tableName = "greetings"
        super().__init__(pool)

    async def insert(self, user_id, gm=False, ga=False, ge=False, gn=False):
        query = f"INSERT INTO {self.tableName} (user_id, gm, ga, ge, gn) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (user_id) DO UPDATE SET gm=$2, ga=$3, ge=$4, gn=$5;"
        await self.execute(query, user_id, gm, ga, ge, gn)

    async def get_users(self, cmd):
        query = f"SELECT * FROM {self.tableName} WHERE {cmd}=true;"
        res = await self.view(query)
        return res


class Analytics(Database):
    """CREATE TABLE analytics (
   id SERIAL PRIMARY KEY,
   command TEXT NOT NULL,
   server_id BIGINT NOT NULL,
   user_id BIGINT NOT NULL,
   time_of_command TIMESTAMP NOT NULL
);"""
    def __init__(self, pool):
        self.tableName = "analytics"
        super().__init__(pool)

    async def insert_command(self, command, server_id, user_id):
        sql = f"INSERT INTO {self.tableName} (command, server_id, user_id, time_of_command) VALUES ($1, $2, $3, $4);"
        await self.execute(sql, command, server_id, user_id, datetime.datetime.now(datetime.UTC).replace(tzinfo=None))

    async def get_summary_stats(self):
        """Return total commands, unique users, unique servers, and recent command counts."""
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        yesterday = now - datetime.timedelta(days=1)
        seven_days_ago = now - datetime.timedelta(days=7)

        sql = f"""
        SELECT
            COUNT(*) AS total_commands,
            COUNT(DISTINCT user_id) AS unique_users,
            COUNT(DISTINCT server_id) FILTER (WHERE server_id IS NOT NULL) AS unique_servers,
            COUNT(*) FILTER (WHERE server_id IS NULL) AS dm_commands,
            COUNT(*) FILTER (WHERE time_of_command >= $1) AS commands_24h,
            COUNT(*) FILTER (WHERE time_of_command >= $2) AS commands_7d
        FROM {self.tableName};
        """
        res = await self.view(sql, yesterday, seven_days_ago)
        if res:
            row = res[0]
            def _extract(key, idx):
                if hasattr(row, "get"):
                    v = row.get(key)
                    if v is not None:
                        return v
                try:
                    return row[key]
                except Exception:
                    try:
                        return row[idx]
                    except Exception:
                        return 0

            return {
                "total_commands": _extract("total_commands", 0) or 0,
                "unique_users": _extract("unique_users", 1) or 0,
                "unique_servers": _extract("unique_servers", 2) or 0,
                "dm_commands": _extract("dm_commands", 3) or 0,
                "commands_24h": _extract("commands_24h", 4) or 0,
                "commands_7d": _extract("commands_7d", 5) or 0,
            }
        return {
            "total_commands": 0,
            "unique_users": 0,
            "unique_servers": 0,
            "dm_commands": 0,
            "commands_24h": 0,
            "commands_7d": 0,
        }

    async def get_top_commands(self, limit=10, days=None):
        """Return top commands by usage, optionally filtered to the last N days."""
        if days:
            cutoff = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) - datetime.timedelta(days=days)
            sql = f"""
            SELECT command, COUNT(*) AS count
            FROM {self.tableName}
            WHERE time_of_command >= $1
            GROUP BY command
            ORDER BY count DESC
            LIMIT $2;
            """
            return await self.view(sql, cutoff, limit)
        sql = f"""
        SELECT command, COUNT(*) AS count
        FROM {self.tableName}
        GROUP BY command
        ORDER BY count DESC
        LIMIT $1;
        """
        return await self.view(sql, limit)

    async def get_server_stats(self, server_id):
        """Return total commands and top commands for a specific server."""
        sql_total = f"SELECT COUNT(*) AS total FROM {self.tableName} WHERE server_id = $1;"
        sql_top = f"""
        SELECT command, COUNT(*) AS count
        FROM {self.tableName}
        WHERE server_id = $1
        GROUP BY command
        ORDER BY count DESC
        LIMIT 5;
        """
        total_res = await self.view(sql_total, server_id)
        top_res = await self.view(sql_top, server_id)
        total = 0
        if total_res:
            row = total_res[0]
            if hasattr(row, "get"):
                total = row.get("total") or 0
            else:
                try:
                    total = row["total"]
                except Exception:
                    total = row[0]
        return {"total_commands": total or 0, "top_commands": top_res or []}


class BollywoodHangmanDB(Database):
    """CREATE TABLE "bollywood_points" (
        "user_id" BIGINT NOT NULL,
        "points" INT,
        "rounds" INT,
        PRIMARY KEY ("user_id")
    );"""

    def __init__(self, pool):
        self.tableName = "bollywood_points"
        super().__init__(pool)

    async def insert_new_entry(self, user_id, points, rounds):
        sql = f"INSERT INTO {self.tableName} (user_id, points, rounds) VALUES ($1, $2, $3);"
        await self.execute(sql, user_id, points, rounds)

    async def update_score(self, user_id, points, rounds):
        await self.execute(
            "INSERT INTO bollywood_points (user_id, points, rounds) VALUES ($1, $2, $3) "
            "ON CONFLICT (user_id) DO UPDATE SET "
            "points = COALESCE(bollywood_points.points, 0) + EXCLUDED.points, "
            "rounds = COALESCE(bollywood_points.rounds, 0) + EXCLUDED.rounds;",
            user_id, points, rounds,
        )


class PlotsterDB(Database):
    """CREATE TABLE "plotster_points" (
        "user_id" BIGINT NOT NULL,
        "points" INT,
        "rounds" INT,
        PRIMARY KEY ("user_id")
    );"""

    def __init__(self, pool):
        self.tableName = "plotster_points"
        super().__init__(pool)

    async def insert_new_entry(self, user_id, points, rounds):
        sql = f"INSERT INTO {self.tableName} (user_id, points, rounds) VALUES ($1, $2, $3);"
        await self.execute(sql, user_id, points, rounds)

    async def update_score(self, user_id, points, rounds):
        await self.execute(
            "INSERT INTO plotster_points (user_id, points, rounds) VALUES ($1, $2, $3) "
            "ON CONFLICT (user_id) DO UPDATE SET "
            "points = COALESCE(plotster_points.points, 0) + EXCLUDED.points, "
            "rounds = COALESCE(plotster_points.rounds, 0) + EXCLUDED.rounds;",
            user_id, points, rounds,
        )


class Coins(Database):
    """CREATE TABLE "points" (
	"user_id" BIGINT NOT NULL,
	"coins" INT NOT NULL,
	PRIMARY KEY ("user_id")
);"""

    def __init__(self, pool):
        self.tableName = "points"
        super().__init__(pool)
        self.read_commands_json()

    def read_commands_json(self):
        with open('commands.json', 'r') as file:
            commands_data = json.load(file)

        self.commands_dict = {command['name']: command for command in commands_data}

    async def add_coins(self, user_id, command_name="", coins=0):
        if coins == 0 and command_name:
            coins = self.commands_dict.get(command_name, {}).get('coins', 0)
        await self.execute(
            "INSERT INTO points (user_id, coins) VALUES ($1, $2) "
            "ON CONFLICT (user_id) DO UPDATE SET coins = points.coins + EXCLUDED.coins;",
            user_id, coins,
        )

    async def transfer(self, sender_id, recipient_id, coins):
        """Move a positive balance atomically, including concurrent transfers."""
        if coins <= 0 or sender_id == recipient_id:
            return False
        async with self.pool.acquire() as con:
            async with con.transaction():
                # Insert and lock accounts in a stable order for opposing transfers.
                for user_id in sorted((sender_id, recipient_id)):
                    await con.execute(
                        "INSERT INTO points (user_id, coins) VALUES ($1, 0) "
                        "ON CONFLICT (user_id) DO NOTHING;", user_id,
                    )
                await con.fetch(
                    "SELECT user_id FROM points WHERE user_id = ANY($1::bigint[]) "
                    "ORDER BY user_id FOR UPDATE;", [sender_id, recipient_id],
                )
                debited = await con.fetchval(
                    "UPDATE points SET coins = coins - $1 "
                    "WHERE user_id = $2 AND coins >= $1 RETURNING user_id;",
                    coins, sender_id,
                )
                if debited is None:
                    return False
                await con.execute(
                    "UPDATE points SET coins = coins + $1 WHERE user_id = $2;",
                    coins, recipient_id,
                )
        return True

    async def deduct_coins(self, user_id, coins=0):
        sql = """UPDATE {}
        SET coins = coins- $1
        WHERE user_id=$2;
        """.format(self.tableName)

        await self.execute(sql, coins, user_id)

    async def get_amount_coins(self, user_id):
        sql = f"""SELECT * FROM {self.tableName} WHERE user_id=$1;"""
        res = await self.view(sql, user_id)
        if len(res) != 0:
            return res[0]
        return {'user_id': user_id, 'coins': 0}

class Characters(Database):
    """
    CREATE TABLE "characters" (
        "user_id" BIGINT NOT NULL,
        "show_name" TEXT,
        "cartoon_character" TEXT,
        "dog_breed" TEXT,
        "cat_breed" TEXT,
        PRIMARY KEY ("user_id")
    );
    """

    def __init__(self, pool):
        self.tableName = "characters"
        super().__init__(pool)

    async def insert_character(self, user_id, show_name=None, cartoon_character=None, dog_breed=None, cat_breed=None):
        """Insert or update a character entry in the table, preserving non-null existing fields"""
        await self.execute(
            "INSERT INTO characters (user_id, show_name, cartoon_character, dog_breed, cat_breed) "
            "VALUES ($1, $2, $3, $4, $5) ON CONFLICT (user_id) DO UPDATE SET "
            "show_name = COALESCE(EXCLUDED.show_name, characters.show_name), "
            "cartoon_character = COALESCE(EXCLUDED.cartoon_character, characters.cartoon_character), "
            "dog_breed = COALESCE(EXCLUDED.dog_breed, characters.dog_breed), "
            "cat_breed = COALESCE(EXCLUDED.cat_breed, characters.cat_breed);",
            user_id, show_name, cartoon_character, dog_breed, cat_breed,
        )

    async def update_character(self, user_id, show_name=None, cartoon_character=None, dog_breed=None, cat_breed=None):
        """Update the details of a character entry in the table"""
        update_fields = []
        query_args = []
        fields = [
            ("show_name", show_name),
            ("cartoon_character", cartoon_character),
            ("dog_breed", dog_breed),
            ("cat_breed", cat_breed)
        ]
        for col, val in fields:
            if val is not None:
                query_args.append(val)
                update_fields.append(f"{col} = ${len(query_args)}")

        if len(update_fields) == 0:
            return  # No fields to update

        update_fields_str = ", ".join(update_fields)
        query_args.append(user_id)

        sql = f"UPDATE {self.tableName} SET {update_fields_str} WHERE user_id = ${len(query_args)};"
        await self.execute(sql, *query_args)

    async def get_character(self, user_id):
        """Fetch the details of a character entry from the table"""
        sql = f"SELECT show_name, cartoon_character, dog_breed, cat_breed FROM {self.tableName} WHERE user_id = $1;"
        result = await self.view(sql, user_id)

        if len(result) != 0:
            return result[0]
        else:
            return None



class DB(Database):
    def __init__(self, pool):
        self.pool = pool
        super().__init__(pool)

        self.analytics = Analytics(pool)
        self.servers = Servers(pool)
        self.greetings = Greetings(pool)
        self.bollywoodHangmanDB = BollywoodHangmanDB(pool)
        self.plotsterDB = PlotsterDB(pool)
        self.coins = Coins(pool)
        self.characters = Characters(pool)
    

