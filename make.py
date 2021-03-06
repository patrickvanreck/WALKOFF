import os


def main():
    print('\nInstalling Python Dependencies...')
    os.system('pip install -r requirements.txt')
    os.system('python installDependencies.py')

    print('\nGenerating Certificates...')
    os.system('python generate_certificates.py')

    print('\nInstalling Node Packages...')
    os.chdir('./client')
    os.system('npm install')

    print('\nInstalling Gulp...')
    os.system('npm install gulp-cli -g')

    print('\nGulping TypeScript Files...')
    os.system('gulp ts')


if __name__ == '__main__':
    main()
