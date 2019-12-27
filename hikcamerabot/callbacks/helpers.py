def get_user_info(update):
    """Return user information who interacts with bot."""
    return 'Request from user_id: {0}, username: {1},' \
           'first_name: {2}, last_name: {3}'.format(
        update.message.chat.id,
        update.message.chat.username,
        update.message.chat.first_name,
        update.message.chat.last_name)


def print_access_error(update):
    """Send authorization error to telegram chat."""
    update.message.reply_text('Not authorized')


def build_commands_presentation(bot, cam_id):
    groups = []
    for desc, cmds in bot.cam_registry.get_commands(cam_id).items():
        groups.append(
            '{0}\n{1}'.format(desc, '\n'.join(['/' + c for c in cmds])))
    return '\n\n'.join(groups)
