# Third-party attribution

This lab uses ROS 2 and the existing Nav2 navigation stack. It does not claim authorship of that stack.

## Nav2 source excerpts and experimental patches

Source: https://github.com/ros-navigation/navigation2

The current main-source experiment is pinned to commit `d7bf2ac06fe778c21c6141eb49b4d3e2c0c82d3a`. Earlier experiments use Nav2 1.3.13 and the Jazzy snapshot recorded in the build scripts and evidence.

The lifecycle-manager source modified by the patch files carries these notices:

- Copyright (c) 2019 Intel Corporation
- Copyright (c) 2022 Samsung Research America

The lifecycle-manager source is licensed under Apache-2.0. A copy of the license is included in `LICENSE`. Patch files in `docs/` and source fragments in the patch-generating scripts contain upstream material and experimental modifications. Applying these patches retains the upstream source headers. The additions implement the lab's cancellation, initialization coordination, context handling, and service QoS experiments; they are not upstream-approved changes.

Nav2 as a whole contains packages with different licenses. Its root license directs users to each package's `package.xml` and file headers. Downloaded dependencies and ROS container images retain their respective licenses; this lab's license does not relicense them. The build scripts download these dependencies separately rather than vendoring the complete source or binaries here.

## Visual notebook

The notebook contains educational diagrams and recorded experiment evidence. It is not a live robot interface. Its design is an original implementation inspired by technical documentation; no US Graphics Company fonts, logos, or image assets are bundled.
