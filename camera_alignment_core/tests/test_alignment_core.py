import logging
import typing

import numpy
import numpy.testing
import numpy.typing
import pytest

from camera_alignment_core.alignment_core import (
    align_image,
    crop,
    generate_alignment_matrix,
)
from camera_alignment_core.channel_info import (
    CameraPosition,
    create_channel_info,
)
from camera_alignment_core.constants import (
    LOGGER_NAME,
    Magnification,
)
from camera_alignment_core.exception import (
    IncompatibleImageException,
)

from . import (
    ALIGNED_ZSD1_IMAGE_URL,
    ARGOLIGHT_OPTICAL_CONTROL_IMAGE_URL,
    UNALIGNED_ZSD1_IMAGE_URL,
    ZSD_100x_OPTICAL_CONTROL_IMAGE_URL,
    get_test_image,
)

log = logging.getLogger(LOGGER_NAME)


class TestAlignmentCore:
    def test_generate_alignment_matrix(self):
        # Arrange
        optical_control_image, _ = get_test_image(ZSD_100x_OPTICAL_CONTROL_IMAGE_URL)
        optical_control_image_data = optical_control_image.get_image_data("CZYX", T=0)

        expected_matrix = numpy.array(
            [
                [1.0013714116607422, -0.0052382809204566, 0.2719881272043381],
                [0.0052382809204566, 1.0013714116607422, -2.940886545198339],
                [0.0, 0.0, 1.0],
            ]
        )

        # Act
        (actual_alignment_matrix, _,) = generate_alignment_matrix(
            optical_control_image_data,
            reference_channel=2,  # TaRFP
            shift_channel=3,  # CMDRP
            magnification=Magnification.ONE_HUNDRED.value,
            px_size_xy=optical_control_image.physical_pixel_sizes.X,
        )

        # Assert
        assert actual_alignment_matrix.shape == expected_matrix.shape

        # Due to inherent challenges with floating point precision across different environments,
        # compare actual vs expected elementwise with a (very) small epsilon (i.e., allowed error margin)
        assert numpy.allclose(actual_alignment_matrix, expected_matrix, atol=1e-14), (
            actual_alignment_matrix - expected_matrix
        )

    def test_generate_alignment_matrix_reproducability(self):
        # Arrange
        optical_control_image, _ = get_test_image(ZSD_100x_OPTICAL_CONTROL_IMAGE_URL)
        optical_control_image_data = optical_control_image.get_image_data("CZYX")

        magnification = Magnification.ONE_HUNDRED.value
        pixel_size_xy = optical_control_image.physical_pixel_sizes.X

        # Act
        (alignment_matrix_1, _,) = generate_alignment_matrix(
            optical_control_image_data,
            reference_channel=2,  # TaRFP
            shift_channel=3,  # CMDRP
            magnification=magnification,
            px_size_xy=pixel_size_xy,
        )
        (alignment_matrix_2, _,) = generate_alignment_matrix(
            optical_control_image_data,
            reference_channel=2,  # TaRFP
            shift_channel=3,  # CMDRP
            magnification=magnification,
            px_size_xy=pixel_size_xy,
        )

        assert numpy.array_equal(alignment_matrix_1, alignment_matrix_2)

    @pytest.mark.parametrize(
        [
            "image_path",
            "alignment_image_path",
            "expectation_image_path",
            "magnification",
        ],
        [
            (
                UNALIGNED_ZSD1_IMAGE_URL,
                ARGOLIGHT_OPTICAL_CONTROL_IMAGE_URL,
                ALIGNED_ZSD1_IMAGE_URL,
                Magnification.ONE_HUNDRED,
            ),
        ],
    )
    def test_align_image(
        self,
        image_path: str,
        alignment_image_path: str,
        expectation_image_path: str,
        magnification: Magnification,
    ):

        # Arrange
        image, local_image_path = get_test_image(image_path)
        channel_info = create_channel_info(local_image_path)
        back_camera_channels = [
            channel.channel_index
            for channel in channel_info.channels
            if channel.camera_position == CameraPosition.BACK
        ]
        optical_control_image, _ = get_test_image(alignment_image_path)
        optical_control_image_data = optical_control_image.get_image_data("CZYX", T=0)

        (alignment_matrix, _,) = generate_alignment_matrix(
            optical_control_image=optical_control_image_data,
            # TaRFP should have been used instead, but H3342 was used as ref channel when ALIGNED_ZSD1_IMAGE_URL was created
            reference_channel=4,  # H3342
            shift_channel=3,  # CMDRP
            magnification=magnification.value,
            px_size_xy=optical_control_image.physical_pixel_sizes.X,
        )

        expectation_image, _ = get_test_image(expectation_image_path)

        # Act
        result = align_image(
            image.get_image_data("CZYX", T=0), alignment_matrix, back_camera_channels
        )

        # expected image is cropped
        cropped_result = crop(result, magnification)

        # Assert
        assert numpy.array_equal(
            cropped_result, expectation_image.get_image_data("CZYX", T=0)
        )

    @pytest.mark.parametrize(
        [
            "image",
            "alignment_matrix",
            "channels",
            "expected_exception",
        ],
        [
            (
                numpy.random.rand(1, 1, 1, 1, 1),  # Wrong dimensions
                numpy.eye(3, 3),
                [0],
                IncompatibleImageException,
            ),
            (
                numpy.random.rand(1, 1, 1, 1),
                numpy.eye(3, 3),
                [],  # Empty channels
                ValueError,
            ),
        ],
    )
    def test_align_image_guards_against_unsupported_parameters(
        self,
        image: numpy.typing.NDArray[numpy.uint16],
        alignment_matrix: numpy.typing.NDArray[numpy.float16],
        channels: typing.List[int],
        expected_exception: typing.Type[Exception],
    ):
        # Act / Assert
        with pytest.raises(expected_exception):
            align_image(image, alignment_matrix, channels)

    # TODO: Add 63x and 20x images to test
    @pytest.mark.parametrize(
        ["image_path", "magnification", "expected_shape"],
        [
            (
                UNALIGNED_ZSD1_IMAGE_URL,
                Magnification(100),
                (4, 75, 600, 900),
            ),
        ],
    )
    def test_crop(
        self,
        image_path,
        magnification,
        expected_shape,
    ):
        # Arrange
        image, _ = get_test_image(image_path)
        image_data = image.get_image_data("CZYX", T=0)

        # Act
        result = crop(image_data, magnification)

        # Assert
        assert result.shape == expected_shape
