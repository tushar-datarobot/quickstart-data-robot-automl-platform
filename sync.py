#!/usr/bin/env python

###########################################################################
#  Copyright 2020 DataRobot Inc. All Rights Reserved.                     #
#                                                                         #
#  This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES       #
#  OR CONDITIONS OF ANY KIND, express or implied.                         #
###########################################################################

import argparse
import boto3
import botocore
from botocore.exceptions import ClientError
import datetime
import os
from urllib.parse import urlparse
import sys
import re
import random
import requests
from timeit import default_timer as timer
import logging
import zipfile
from zipfile import BadZipfile
import json

try:
  import pwd
except ImportError:
  import getpass
  pwd = None

#setup simple logging for INFO.
logger = logging.getLogger()

def makeArgs():
    parser = argparse.ArgumentParser(
        prog='PROG',
        usage='%(prog)s [options]',
        # formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        formatter_class=argparse.RawTextHelpFormatter,
        # formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""Syncs your current template directory to a defined S3 bucket.
        
""",
        epilog="DataRobot Copyright 2020"
    )
    parser.add_argument("--s3bucket", help="Name of your bucket. Default: %(default)s", required=True )
    parser.add_argument("--region", help="Name of your bucket. Default: %(default)s", default="us-east-1" )
    args = parser.parse_args()

    return args


def bucketExists(bucket):
    """Determine whether bucket exists and the user has permission to access it

    :param bucket: string
    :return: True if the referenced bucket_name exists, otherwise False
    """

    s3 = boto3.client('s3')
    try:
        response = s3.head_bucket(Bucket=bucket)
        logging.debug("*** Bucket Check Response: %s" % response)
    except ClientError as e:
        logging.debug(e)
        return False
    return True

def createBucket(bucket, region=None):
    """Create an S3 bucket in a specified region

    If a region is not specified, the bucket is created in the S3 default
    region (us-east-1).

    :param bucket: String S3 bucket to create
    :param region: String region to create bucket in, e.g., 'us-west-2'
    :return: True if bucket created, else False
    """

    try:
        if region == "us-east-1":
            region == None

        # Check if my bucket exists
        if bucketExists(bucket) is True:
            logging.debug("== Bucket '%s' already exists in '%s'" % (bucket, region) )
        else:
            if region is None:
                s3 = boto3.client( 's3' )
                response = s3.create_bucket(Bucket=bucket)
                logging.info("response: %s" % (response))

            else:
                s3 = boto3.client( 's3', region_name=region )
                response = s3.create_bucket( Bucket=bucket )

            logging.debug("== Create Bucket Response: %s" % response)

    except ClientError as e:
        logging.error(e)
        return False
    return True

def makeStorageDir( bucket, storagedir ):
    file = "readme.txt"
    s3 = boto3.resource('s3')
    try:
        s3.Bucket(bucket).upload_file( file, "%s/%s" % ( storagedir, file ) )
        logging.info("Created file storage directory: s3://%s/%s" % ( bucket, storagedir ))

    except ClientError as ce:
        logging.error("s3://%s/%s/%s creation error: %s" % ( bucket, storagedir, file, ce))
        return False

    return True

def uploadFiles( bucket ):
    """Upload the files in the current diretory to the given bucket

    :param bucket: string
    :return: Number of files uploaded to the bucket
    """

    s3 = boto3.resource('s3')

    fcount = 0
    try:
        rootpath = "%s/" % os.getcwd()

        for path, subdirs, files in os.walk(rootpath):
            path = path.replace(rootpath, "").replace("\\","/")
            for file in files:

                if file == '.DS_Store' or path == 'debug':
                    continue

                file = ("%s/%s" %(path, file)).strip("/")
                fullpath = "%s%s" %(rootpath, file)
                fcount += 1
                s3.Bucket(bucket).upload_file( fullpath, file )
                logging.info("synced ./%s -> s3://%s/%s" %(fullpath.replace(rootpath, ""), bucket, file) )

    except ClientError as ce:
        logging.error("S3 Sync Error: %s" % ce)

    return fcount

# Declare the function to return all file paths of a particular directory
def retrieve_file_paths(dirName):
    # setup file paths variable
    filePaths = []

    # Read all directory, subdirectories and file lists
    for root, directories, files in os.walk(dirName):
        for filename in files:
            # Create the full filepath by using os module.
            filePath = os.path.join(root, filename)
            filePaths.append(filePath)

    # return all paths
    return filePaths

def main():
    try:
        logger.setLevel(logging.INFO)
        logging.basicConfig(format='%(message)s', level=logging.INFO)
        # Get the arguments
        args = makeArgs()
        # Announce what is going on
        logging.info("=== Started %s ===" %( os.path.basename(sys.argv[0])))

        # # Create the S3 file storage directory
        # if args.storagetype == "s3bucket":
        #     makeStorageDir( args.s3bucket, args.s3storagedir )

        client = boto3.client('sts')       

        # Create the bucket as required
        if createBucket( args.s3bucket, args.region ):
            logging.info("Bucket '%s' in region '%s' is ready." % (args.s3bucket, args.region) )

        # Create the S3 file storage directory
        makeStorageDir( args.s3bucket, 'templates' )
        # Upload the files to the bucket
        result = uploadFiles(args.s3bucket)
        logging.info("Uploaded %s files to s3://%s" % (result, args.s3bucket) )
    except ValueError as e:
        logging.error("Invalid parameter error: %s" % e)

if __name__ == '__main__':
    main()


