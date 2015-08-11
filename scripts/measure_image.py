import sys
import os
from argparse import ArgumentParser
import re
import datetime
import astropy.units as u
import IQMon

def measure_image(file,\
                 clobber_logs=False,\
                 verbose=False,\
                 nographics=False,\
                 analyze_image=True,\
                 record=True,\
                 zero_point=False,\
                 ):

    ##-------------------------------------------------------------------------
    ## Create Telescope Object
    ##-------------------------------------------------------------------------
    config_file = os.path.join('/', 'var', 'panoptes', 'panoptes.yaml')
    tel = IQMon.Telescope(config_file)

    ##-------------------------------------------------------------------------
    ## Perform Actual Image Analysis
    ##-------------------------------------------------------------------------
    with IQMon.Image(file, tel) as im:
        im.make_logger(verbose=verbose, clobber=clobber_logs)
        im.read_image()
        if analyze_image:
            if image.tel.ROI:
                image.crop()
            image.run_SExtractor()
            image.determine_FWHM()

            is_blank = (image.n_stars_SExtracted < 100)
            if is_blank:
                image.logger.warning('Only {} stars found.  Image may be blank.'.format(image.n_stars_SExtracted))

            if not image.image_WCS and not is_blank:
                image.solve_astrometry()
                image.run_SExtractor()
            image.determine_pointing_error()

            if zero_point and not is_blank:
                image.run_SCAMP()
                if image.SCAMP_successful:
                    image.run_SWarp()
                    image.get_catalog()
                    image.run_SExtractor(assoc=True)
                    image.determine_FWHM()
                    image.measure_zero_point(plot=True)
                    mark_catalog = True
                else:
                    image.logger.info('  SCAMP failed.  Skipping photometric calculations.')

            if not nographics and image.FWHM:
                try:
                    image.make_PSF_plot()
                except:
                    image.logger.warning('Failed to make PSF plot')

        if record and not nographics:
            p1, p2 = (1.50, 0.50)
            small_JPEG = image.raw_file_basename+"_fullframe.jpg"
            image.make_JPEG(small_JPEG, binning=2,\
                            p1=p1, p2=p2,\
                            make_hist=False,\
                            mark_pointing=True,\
                            mark_detected_stars=True,\
                            mark_catalog_stars=True,\
                            mark_saturated=False,\
                            quality=70,\
                            )
            cropped_JPEG = image.raw_file_basename+"_crop.jpg"
            image.make_JPEG(cropped_JPEG,\
                            p1=p1, p2=p2,\
                            make_hist=False,\
                            mark_pointing=True,\
                            mark_detected_stars=True,\
                            mark_catalog_stars=False,\
                            mark_saturated=False,\
                            crop=(int(image.nXPix/2)-800, int(image.nYPix/2)-800, int(image.nXPix/2)+800, int(image.nYPix/2)+800),\
                            quality=40,\
                            )

        image.clean_up()
        image.calculate_process_time()

        if record:
            image.add_mongo_entry()

        image.logger.info('Done.')


def main():
    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = ArgumentParser(description="Describe the script")
    ## add flags
    parser.add_argument("-v", "--verbose",
        action="store_true", dest="verbose",
        default=False, help="Be verbose! (default = False)")
    parser.add_argument("--no-graphics",
        action="store_true", dest="nographics",
        default=False, help="Turn off generation of graphics")
    parser.add_argument("-z", "--zp",
        action="store_true", dest="zero_point",
        default=False, help="Calculate zero point")
    parser.add_argument("-n", "--norecord",
        action="store_true", dest="no_record",
        default=False, help="Do not record results")
    ## add arguments
    parser.add_argument("filename",
        type=str,
        help="File Name of Input Image File")
    args = parser.parse_args()

    record = not args.no_record

    measure_image(args.filename,\
                  telescope=args.telescope,\
                  nographics=args.nographics,\
                  zero_point=args.zero_point,\
                  record=record,\
                  verbose=args.verbose)


if __name__ == '__main__':
    main()
