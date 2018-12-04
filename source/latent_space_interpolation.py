""" script for generating samples from a trained model """

import argparse
import os

import torch as th

# define the device for the training script
device = th.device("cuda" if th.cuda.is_available() else "cpu")

# set manual seed to 3
th.manual_seed(3)


def parse_arguments():
    """
    command line arguments parser
    :return: args => parsed command line arguments
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("--generator_file", action="store", type=str,
                        help="pretrained weights file for generator", required=True)

    parser.add_argument("--latent_size", action="store", type=int,
                        default=512,
                        help="latent size for the generator")

    parser.add_argument("--num_samples", action="store", type=int,
                        default=64,
                        help="number of samples in the sheet (preferably a square number)")

    parser.add_argument("--size", action="store", type=int,
                        default=128,
                        help="latent size for the generator")

    parser.add_argument("--time", action="store", type=float,
                        default=1,
                        help="Number of minutes for the video to make")

    parser.add_argument("--std", action="store", type=float, default=1,
                        help="Truncated standard deviation fo the drawn samples")

    parser.add_argument("--traversal_time", action="store", type=float,
                        default=3,
                        help="Number of seconds to go from one point to another")

    parser.add_argument("--static_time", action="store", type=float,
                        default=1,
                        help="Number of seconds to display a sample")

    parser.add_argument("--fps", action="store", type=int,
                        default=30, help="Frames per second in the video")

    parser.add_argument("--out_dir", action="store", type=str,
                        default="interp_animation_frames/",
                        help="path to the output directory for the frames")

    args = parser.parse_args()

    return args


def main(args):
    """
    Main function of the script
    :param args: parsed commandline arguments
    :return: None
    """
    from vdb.Gan_networks import Generator
    from vdb.Gan import GAN

    # create generator object:
    print("Creating a generator object ...")
    generator = th.nn.DataParallel(
        Generator(size=args.size,
                  z_dim=args.latent_size,
                  final_channels=64,
                  max_channels=1024).to(device))

    # load the trained generator weights
    print("loading the trained generator weights ...")
    generator.load_state_dict(th.load(args.generator_file))

    # total_frames in the video:
    total_time_for_one_transition = args.traversal_time + args.static_time
    total_frames_for_one_transition = (total_time_for_one_transition * args.fps)
    number_of_transitions = int((args.time * 60) / total_time_for_one_transition)
    total_frames = int(number_of_transitions * total_frames_for_one_transition)

    # Let's create the animation video from the latent space interpolation
    # I save the frames required for making the video here
    points_1 = th.randn(args.num_samples, args.latent_size).to(device) * args.std

    # create output directory
    os.makedirs(args.out_dir, exist_ok=True)

    # Run the main loop for the interpolation:
    global_frame_counter = 1  # counts number of frames
    while global_frame_counter <= total_frames:
        points_2 = th.randn(args.num_samples, args.latent_size).to(device) * args.std
        direction = points_2 - points_1

        # create the points for images in this space:
        number_of_points = int(args.traversal_time * args.fps)
        for i in range(number_of_points):
            points = points_1 + ((direction / number_of_points) * i)

            # generate the image for this point:
            img = generator(points)

            # save the image:
            GAN.create_grid(img, os.path.join(args.out_dir, str(global_frame_counter) + ".png"))

            # increment the counter:
            global_frame_counter += 1

        # at point_2, now add static frames:
        img = generator(points_2)

        # now save the same image a number of times:
        for _ in range(int(args.static_time * args.fps)):
            GAN.create_grid(img, os.path.join(args.out_dir, str(global_frame_counter) + ".png"))
            global_frame_counter += 1

        # set the point_1 := point_2
        points_1 = points_2

        print("Generated %d frames ..." % global_frame_counter)

    # video frames have been generated
    print("Video frames have been generated at:", args.out_dir)


if __name__ == "__main__":
    main(parse_arguments())
