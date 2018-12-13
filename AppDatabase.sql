/* Setup file for project database */
create user if not exists 'appserver'@'localhost' identified by 'team7';
drop database if exists AppDb;
create database AppDb;
grant all privileges on AppDb.* to 'appserver'@'localhost' identified by 'team7';

/* Table creation */
use AppDb;

create table if not exists users (
    userId int not null auto_increment primary key,
    fullName varchar( 128 ),
    password varchar( 256 ),
    lastNotification int default 0
);

create table if not exists messages (
    msgId int not null auto_increment primary key,
    posterId int not null,
    wallOwnerId int not null,
    posterName varchar( 128 ),
    wallOwnerName varchar( 128 ),
    msg varchar( 4095 ),
    created datetime,
    foreign key fkPoster(posterId)
    references users(userId)
    on update cascade
    on delete restrict,
    foreign key fkWallOwner(wallOwnerId)
    references users(userId)
    on update cascade
    on delete restrict
);