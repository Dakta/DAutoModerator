import sys, os
from ConfigParser import SafeConfigParser


import sqlalchemy
from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import *


cfg_file = SafeConfigParser()
path_to_cfg = os.path.abspath(os.path.dirname(sys.argv[0]))
path_to_cfg = os.path.join(path_to_cfg, 'modbot.cfg')
cfg_file.read(path_to_cfg)

db_config = \
    cfg_file.get('database', 'system')+'://'+\
    cfg_file.get('database', 'username')+':'+\
    cfg_file.get('database', 'password')+'@'+\
    cfg_file.get('database', 'host')+'/'+\
    cfg_file.get('database', 'database')


# Create SQLAlchemy database engine
engine = create_engine(db_config)
# Create configured Session object
Session = sessionmaker(engine)

# create a new session object
session = Session()

# Create a base table class
Base = declarative_base()

# Creates all tables in the Base table class
# Base.metadata.create_all(engine)


class Subreddit(Base):

    """Table containing the subreddits for the bot to monitor.

    name - The subreddit's name. "gaming", not "/r/gaming".
    network - If the subreddit is part of a network, the network's short name. e.g. "sfwpn"
    enabled - Subreddit will not be checked if False
    last_submission - The newest unfiltered submission the bot has seen
    last_spam - The newest filtered submission the bot has seen
    report_threshold - Any items with at least this many reports will trigger
        a mod-mail alert
    auto_reapprove - If True, bot will reapprove any reported submissions
        that were previously approved by a human mod - use with care
    check_all_conditions - If True, the bot will not stop and perform the
        action as soon as a single condition is matched, but will create
        a list of all matching conditions. This can be useful for subreddits
        with strict rules where a comment should include all reasons the post
        was removed.
    reported_comments_only - If True, will only check conditions against
        reported comments. If False, checks all comments in the subreddit.
        Extremely-active subreddits are probably best set to True.

    """

    __tablename__ = 'subreddits'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    network = Column(Integer, ForeignKey('networks.id'), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    last_submission = Column(DateTime, nullable=False)
    last_spam = Column(DateTime, nullable=False)
    last_comment = Column(DateTime, nullable=False)
    auto_reapprove = Column(Boolean, nullable=False, default=False)
    check_all_conditions = Column(Boolean, nullable=False, default=False)
    reported_comments_only = Column(Boolean, nullable=False, default=False)

class Network(Base):
    
    """Table containing a list of subreddit networks, groups of subreddits that
        share moderators, rules, etc.
    
    short_name - the short name of the network. e.g. "sfwpn"
    name - the long name of the network. e.g. "Safe for Work Porn Network"
    enabled - network will be ignored if False
    network_subreddit - if the network has a master subreddit, that subreddit's name.
    moderation_subreddit - Subreddit to post removals to, ala r/ModerationPorn
    network_mods - if True, all mods of all network subreddits will be made mods
        of the master subreddit. requires valid `subreddit`
    network_contribs - if True, all mods of all network subreddits will be made
        approved submitters of the master subreddit. requires valid `subreddit`
    
    """
    
    __tablename__ = 'networks'
    
    id = Column(Integer, primary_key=True)
    short_name = Column(String(100), nullable=False, unique=True)
    name = Column(String(500), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    network_subreddit = Column(String(100), nullable=True)
    moderation_subreddit = Column(String(100), nullable=True)
    network_mods = Column(Boolean, nullable=False, default=False)
    network_contribs = Column(Boolean, nullable=False, default=False)


class Condition(Base):

    """Table containing the conditions for each subreddit.

    subreddit_id - which subreddit this condition applies to. Null if network
        condition
    network_id - which network this condition applies to. Null if subreddit
        condition
    network_id
    subject - The type of item to check
    attribute - Which attribute of the item to check
    value - A regex checked against the attribute. Automatically surrounded
        by ^ and $ when checked, so looks for "whole string" matches. To
        do a "contains" check, put .* on each end
    num_reports - The number of reports the item has. Note that setting to
        None means a matching item *must* have 0 reports.
    auto_reapproving - Whether the num_reports condition should apply only
        during auto-reapproving, only before, or both (if null)
    is_gold - Whether the author has reddit gold or not
    is_shadowbanned - Whether the author is "shadowbanned" or not
    account_age - Account age condition (in days) for the item's author
    link_karma - Link karma condition for the item's author
    comment_karma - Comment karma condition for the item's author
    combined_karma - Combined karma condition for the item's author
    account_rank - Whether the author is an approved submitter ("contributor")
        or moderator in the subreddit - note that a moderator will also be
        considered to be a contributor
    inverse - If True, result of check will be reversed. Useful for
        "anything except" or "does not include"-type checks
    parent_id - The id of the condition this is a sub-condition of. If this
        is a top-level condition, will be null
    action - Which action to perform if this condition is matched
    spam - Whether to train the spam filter if this is a removal
    comment_method - What method the bot should use to deliver its comment
        when this condition is matched - reply to the item itself, send
        a PM to the item's author, or modmail to the subreddit
    log_method - If 'submit', bot will submit the removal to its network's
        moderation_subreddit
    comment - If set, bot will post this comment using the defined method
        when this condition is matched
    notes - not used by bot, space to keep notes on a condition

    """

    __tablename__ = 'conditions'

    id = Column(Integer, primary_key=True)
    subreddit_id = Column(Integer, ForeignKey('subreddits.id'), nullable=True)
    network_id = Column(Integer, ForeignKey('networks.id'), nullable=True)
    subject = Column(Enum('submission',
                          'comment',
                          'both',
                          name='condition_subject'),
                     nullable=False)
    attribute = Column(Enum('user',
                            'title',
                            'domain',
                            'url',
                            'body',
                            'media_user',
                            'media_title',
                            'media_description',
                            'author_flair_text',
                            'author_flair_css_class',
                            'meme_name',
                            name='condition_attribute'),
                       nullable=False)
    value = Column(Text, nullable=False)
    num_reports = Column(Integer)
    auto_reapproving = Column(Boolean, default=False)
    is_gold = Column(Boolean)
    is_shadowbanned = Column(Boolean)
    account_age = Column(Integer)
    link_karma = Column(Integer)
    comment_karma = Column(Integer)
    combined_karma = Column(Integer)
    account_rank = Column(Enum('contributor',
                               'moderator',
                               name='rank'))
    inverse = Column(Boolean, nullable=False, default=False)
    parent_id = Column(Integer, ForeignKey('conditions.id'))
    action = Column(Enum('approve',
                         'remove',
                         'alert',
                         'set_flair',
                         name='action'))
    spam = Column(Boolean)
    set_flair_text = Column(Text)
    set_flair_class = Column(String(255))
    comment_method = Column(Enum('comment',
                                 'message',
                                 'modmail',
                                 name='comment_method'))
    log_method = Column(Enum('none',
                             'submit',
                             name='log_method'))
    comment = Column(Text)
    notes = Column(Text)
    short_reason = Column(String(255))

    subreddit = relationship('Subreddit',
        backref=backref('conditions', lazy='dynamic'))

    additional_conditions = relationship('Condition',
        lazy='joined', join_depth=1)


class ActionLog(Base):
    """Table containing a log of the bot's actions."""
    __tablename__ = 'action_log'

    id = Column(Integer, primary_key=True)
    subreddit_id = Column(Integer,
                          ForeignKey('subreddits.id'),
                          nullable=False)
    title = Column(Text)
    user = Column(String(255))
    url = Column(Text)
    domain = Column(String(255))
    permalink = Column(String(255))
    created_utc = Column(DateTime)
    action_time = Column(DateTime)
    action = Column(Enum('approve',
                         'remove',
                         'alert',
                         'set_flair',
                         name='action'))
    matched_condition = Column(Integer, ForeignKey('conditions.id'))

    subreddit = relationship('Subreddit',
        backref=backref('actions', lazy='dynamic'))

    condition = relationship('Condition',
        backref=backref('actions', lazy='dynamic'))


class AutoReapproval(Base):
    """Table keeping track of posts that have been auto-reapproved."""
    __tablename__ = 'auto_reapprovals'

    id = Column(Integer, primary_key=True)
    subreddit_id = Column(Integer,
                          ForeignKey('subreddits.id'),
                          nullable=False)
    permalink = Column(String(255))
    original_approver = Column(String(255))
    total_reports = Column(Integer, nullable=False, default=0)
    first_approval_time = Column(DateTime)
    last_approval_time = Column(DateTime)

    subreddit = relationship('Subreddit',
        backref=backref('auto_reapprovals', lazy='dynamic'))


# import datetime
# dakta_sub = Subreddit()
# dakta_sub.id = 1
# dakta_sub.name = 'dakta'
# dakta_sub.network = 1
# dakta_sub.enabled = 1
# dakta_sub.last_submission = datetime.datetime.now()
# dakta_sub.last_spam = datetime.datetime.now()
# dakta_sub.last_comment = datetime.datetime.now()
# dakta_sub.auto_reapprove = 0
# dakta_sub.check_all_conditions = 1
# dakta_sub.reported_comments_only = 0
# 
# session.add(dakta_sub)
# session.commit()

# db.create_all()
# Base.metadata.create_all(engine)