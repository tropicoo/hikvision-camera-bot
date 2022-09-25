from asyncio.subprocess import Process


async def get_stdout_stderr(proc: Process) -> tuple[str, str]:
    stdout, stderr = await proc.stdout.read(), await proc.stderr.read()
    return stdout.decode().strip(), stderr.decode().strip()
