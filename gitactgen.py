#!/bin/python3
import argparse, datetime, math, shutil, subprocess, os
from PIL import Image

parser = argparse.ArgumentParser()
parser.add_argument('git_name', type=str, help='name of the commit author')
parser.add_argument('git_email', type=str, help='email of the commit author')
parser.add_argument('year', type=int, help='year to generate the commits for')
parser.add_argument('-s', '--strength', type=int, help='max commits per day, scaled by alpha values', default=5)
parser.add_argument('-f', '--force', action='store_true', help='overwrite existing files')
parser.add_argument('-o', '--output', type=str, help='output path for the git repository, defaults to \'activity-repo\'', default='activity-repo')
parser.add_argument('-y', action='store_true', help='skip confirmation')
parser.add_argument('--no-preview', action='store_true', help='don\'t show a terminal preview')

subparsers = parser.add_subparsers(dest='subcommand', required=True)
img_parser = subparsers.add_parser('image', help='generate activity commits from an image.')
img_parser.add_argument('image_file', type=str, help='path to image input')

text_parser = subparsers.add_parser('text', help='generate activity commits from text with a glyphs file')
text_parser.add_argument('glyphs_file', type=str, help='input path for the glyphs file')
text_parser.add_argument('text', type=str, help='input of text to generate')

args = parser.parse_args()

grid = []
if args.subcommand == 'image':
    img = Image.open(args.image_file)
    img_width, img_height = img.size
    print('Image size: {}x{}'.format(img_width, img_height))
    if img_width > 52 or img_height > 7:
        print('Error: image is too big, maximum size is 52x7')
        quit()
    for x in range(img_width):
        for y in range(7):
            if y < img_height:
                r,g,b,a = img.getpixel((x, y))
                grid.append(a)
            else:
                grid.append(0)
elif args.subcommand == 'text':
    GLYPH_HEIGHT = 7
    CHARSET = [' ', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '!', '?']
    glyphs = {}
    img = Image.open(args.glyphs_file)
    current = []
    n = 0
    for x in range(img.width):
        if n >= len(CHARSET):
            break

        for y in range(img.height):
            r,g,b,a = img.getpixel((x, y))
            # End a glyph on a red pixel
            if r == 255 and a == 255:
                current.append(0)
                glyphs[CHARSET[n]] = list(current)
                current.clear()
                n += 1
            else:
                current.append(a)
    for c in args.text:
        if not c in glyphs:
            print('Warning: the character \'{}\' is skipped because it has no glyph!'.format(c))
            continue
        grid += glyphs[c]

grid_width = len(grid) // 7

if args.subcommand == 'text':
    print('Generated image width is {} pixels'.format(grid_width))
    if grid_width > 52:
        print('Error: image size exceeds available space: make your text shorter')
        quit()

if not args.no_preview:
    b_side = math.ceil((grid_width - 15)/2)
    print(b_side * '=', 'Image Preview', b_side * '=')
    for y in range(7):
        row = ''
        for x in range(grid_width):
            val = grid[x * 7 + y]
            if val <= 0:
                row += ' '
            elif val < 255:
                row += '░'
            else:
                row += '█'
        print(row)
    print(grid_width * '=')

if not args.y:
    confirm = input('Continue [Y/n] ')
    if confirm.lower() != 'y':
        print('Cancelled')
        quit()

create_repo = True
if os.path.isdir(args.output):
    if os.path.isdir(args.output + '/.git'):
        create_repo = False
        print('Adding commits to existing repository')
    else:
        if not args.force:
            print('Error: path already exists, use the force (-f) flag to overwrite existsting files')
            quit()
        else:
            shutil.rmtree(args.output)
else:
    os.makedirs(args.output)

os.chdir(args.output)
def run_cmd(cmd):
    subprocess.run(cmd, shell=True, check=True)

if create_repo:
    run_cmd('git init --quiet')
    run_cmd('git config user.name {}'.format(args.git_name))
    run_cmd('git config user.email {}'.format(args.git_email))

# Start on first sunday of year
first_doy = datetime.date(args.year, 1, 1)
first_sunday = first_doy + datetime.timedelta(days=6 - first_doy.weekday())

total_pixels = grid_width*7
counter = 0
total_commits = math.floor(sum(grid) / 255 * args.strength)
for x in range(grid_width):
    for y in range(7):
        n = x * 7 + y
        val = grid[n]
        commit_count = math.floor(val / 255 * args.strength)
        date = first_sunday + datetime.timedelta(days=n)
        date_str = date.strftime('%Y-%m-%dT12:00:00')
        for i in range(commit_count):
            with open('activity.txt', 'w') as f:
                f.write('{} {}/{}\n'.format(date, i, commit_count))
            run_cmd('git add .')
            run_cmd('git commit --quiet --date "{}" -m "pixel {}, commit {}/{}"'.format(date_str, n, i+1, commit_count));
        counter += commit_count
        progress = counter / total_commits
        progress_bar = (math.floor(progress * 26 - 1) * '=' + '>').ljust(26, ' ')
        print('\rGenerating [{}]  {:>6}/{:<6}'.format(progress_bar, counter, total_commits).ljust(60), end='')
print('\rGenerated {} commits'.format(counter).ljust(60))
print('Done! Created repository \'{}\''.format(args.output))
