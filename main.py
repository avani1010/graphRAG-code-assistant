from parser.multi_repo_parser import MultiRepoParser

def main():
    multi_parser = MultiRepoParser()

    try:
        multi_parser.parse_all_repos(clear_db=True)
    finally:
        multi_parser.close()


if __name__ == '__main__':
    main()